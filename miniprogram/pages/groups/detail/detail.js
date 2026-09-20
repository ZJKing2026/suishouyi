// pages/groups/detail/detail.js
import { request } from '../../../utils/request.js';
import { getUser } from '../../../utils/auth.js';

Page({
  data: {
    groupId: 0,
    myId: 0,
    group: null,
    members: [],
    isOwner: false,
    messages: [],
    inputText: '',
    useAI: false,
    scrollToId: '',

    // 邀请好友弹层
    showInvite: false,
    selectable: [],       // 可邀请的好友（已排除群内成员）
    selected: {},         // { friend_id: true }，供 wxml 直接取
    selectedCount: 0,

    aiRunning: false
  },

  onLoad(options) {
    const user = getUser();
    this.setData({
      groupId: parseInt(options.id),
      myId: user ? user.id : 0
    });
    this.loadGroup();
  },

  onShow() { this.loadGroup(); },

  // ==================== 加载群详情 ====================
  async loadGroup() {
    try {
      const res = await request(`/groups/${this.data.groupId}`, 'GET');
      this.setData({
        group: res.group,
        members: res.members,
        messages: res.messages,
        isOwner: res.group.owner_id === this.data.myId
      });
      wx.setNavigationBarTitle({ title: res.group.name });
      this.scrollToBottom();
    } catch (err) {
      console.error('加载群详情失败:', err);
    }
  },

  // ==================== 发消息 ====================
  onInput(e) { this.setData({ inputText: e.detail.value }); },

  onToggleAI() { this.setData({ useAI: !this.data.useAI }); },

  async onSend() {
    const text = this.data.inputText.trim();
    if (!text) return;
    try {
      await request(`/groups/${this.data.groupId}/send`, 'POST', {
        content: text,
        use_ai: this.data.useAI
      });
      this.setData({ inputText: '' });
      this.loadGroup();
    } catch (err) {
      wx.showToast({ title: err.message, icon: 'none' });
    }
  },

  // ==================== 邀请好友 ====================
  async onOpenInvite() {
    wx.showLoading({ title: '加载中...', mask: true });
    try {
      const res = await request('/friends', 'GET');
      wx.hideLoading();

      const memberIds = this.data.members.map(m => m.user_id);
      const selectable = res.friends.filter(f => memberIds.indexOf(f.friend_id) === -1);

      if (selectable.length === 0) {
        wx.showModal({
          title: '没有可邀请的好友',
          content: '你的好友都已经在这个群里了。\n先去「好友」页生成邀请码，加几个新好友吧。',
          showCancel: false
        });
        return;
      }

      this.setData({ showInvite: true, selectable, selected: {}, selectedCount: 0 });
    } catch (err) {
      wx.hideLoading();
      console.error('加载好友失败:', err);
      wx.showToast({ title: '加载好友失败', icon: 'none' });
    }
  },

  onCloseInvite() { this.setData({ showInvite: false }); },

  // 阻止弹层内部点击冒泡到遮罩
  noop() {},

  onToggleSelect(e) {
    const id = e.currentTarget.dataset.id;
    const on = !this.data.selected[id];

    const selected = Object.assign({}, this.data.selected);
    if (on) {
      selected[id] = true;
    } else {
      delete selected[id];
    }

    this.setData({
      selected,
      selectedCount: Object.keys(selected).length
    });
  },

  async onConfirmInvite() {
    const ids = Object.keys(this.data.selected).map(k => parseInt(k));
    if (ids.length === 0) {
      wx.showToast({ title: '先选好友', icon: 'none' });
      return;
    }

    wx.showLoading({ title: '邀请中...', mask: true });
    try {
      const res = await request(`/groups/${this.data.groupId}/members`, 'POST', {
        member_ids: ids
      });
      wx.hideLoading();
      this.setData({ showInvite: false });

      const names = (res.added_names || []).join('、');
      wx.showToast({
        title: names ? `已邀请 ${names}` : '邀请完成',
        icon: 'none',
        duration: 2500
      });
      this.loadGroup();
    } catch (err) {
      wx.hideLoading();
      wx.showModal({ title: '邀请失败', content: err.message, showCancel: false });
    }
  },

  // ==================== AI 自主讨论 ====================
  onStartDiscussion() {
    if (this.data.aiRunning) {
      wx.showToast({ title: '讨论进行中，请稍候', icon: 'none' });
      return;
    }
    if (this.data.members.length < 2) {
      wx.showModal({
        title: '人数不够',
        content: '群里至少要有 2 个人，AI 才能替大家讨论。\n先邀请一个好友进群吧。',
        showCancel: false
      });
      return;
    }

    wx.showModal({
      title: '🤖 让 AI 讨论',
      content: '群里每个人的 AI 会轮流发言，聊完自动总结',
      editable: true,
      placeholderText: '讨论什么？比如"国庆去哪玩"',
      success: (r) => {
        if (r.confirm && r.content && r.content.trim()) {
          this.doStartDiscussion(r.content.trim());
        }
      }
    });
  },

  async doStartDiscussion(topic) {
    this.setData({ aiRunning: true });
    wx.showLoading({ title: 'AI 讨论中...', mask: true });

    try {
      // 后端只建任务就返回，讨论在后台跑，这里轮询进度
      const task = await request(`/groups/${this.data.groupId}/ai-discussion`, 'POST', {
        topic: topic
      });
      this.pollDiscussion(task.id);
    } catch (err) {
      wx.hideLoading();
      this.setData({ aiRunning: false });
      wx.showModal({
        title: '讨论失败',
        content: err.message || '请稍后再试',
        showCancel: false
      });
    }
  },

  /** 轮询讨论任务，跑完再收工 */
  pollDiscussion(taskId) {
    let tries = 0;
    const MAX_TRIES = 60;          // 最多等 3 分钟

    const timer = setInterval(async () => {
      tries += 1;
      try {
        const task = await request(`/agent-tasks/${taskId}`, 'GET');

        if (task.status === 'done' || task.status === 'failed') {
          clearInterval(timer);
          wx.hideLoading();
          this.setData({ aiRunning: false });
          this.loadGroup();

          if (task.status === 'failed') {
            wx.showModal({
              title: '讨论失败',
              content: task.error || '请稍后再试',
              showCancel: false
            });
            return;
          }
          wx.showModal({
            title: '✅ 讨论完成',
            content: (task.result && task.result.summary) || '讨论已结束',
            showCancel: false,
            confirmText: '查看记录'
          });
          return;
        }
      } catch (err) {
        console.error('轮询讨论失败:', err);
      }

      if (tries >= MAX_TRIES) {
        clearInterval(timer);
        wx.hideLoading();
        this.setData({ aiRunning: false });
        wx.showToast({ title: '讨论还在进行，稍后回来看', icon: 'none', duration: 2500 });
        this.loadGroup();
      }
    }, 3000);
  },

  // ==================== 滚动到底 ====================
  scrollToBottom() {
    setTimeout(() => {
      const msgs = this.data.messages;
      if (msgs.length > 0) {
        this.setData({ scrollToId: 'msg-' + msgs[msgs.length - 1].id });
      }
    }, 100);
  }
})
