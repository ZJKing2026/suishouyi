// pages/friends/chat/chat.js
import { request } from '../../../utils/request.js';
import { getUser } from '../../../utils/auth.js';
import { parseMarkdown } from '../../../utils/markdown.js';

Page({
  data: {
    friendId: 0,
    friendName: '',
    myId: 0,
    messages: [],
    inputText: '',
    scrollToId: '',
    aiRunning: false       // 标记 AI 是否正在跑
  },

  onLoad(options) {
    const user = getUser();
    this.setData({
      friendId: parseInt(options.friend_id),
      friendName: decodeURIComponent(options.name || '好友'),
      myId: user ? user.id : 0,
    });
    this.loadMessages();
  },

  onShow() {
    this.loadMessages();
  },

  // ==================== 加载消息 ====================
  async loadMessages() {
    try {
      const res = await request(`/friends/${this.data.friendId}/messages`, 'GET');
      this.setData({ messages: res.messages });
      this.scrollToBottom();
    } catch (err) {
      console.error('加载消息失败:', err);
    }
  },

  onInput(e) {
    this.setData({ inputText: e.detail.value });
  },

  // ==================== 手动发消息 ====================
  async onSend() {
    const text = this.data.inputText.trim();
    if (!text) return;
    try {
      await request(`/friends/${this.data.friendId}/send`, 'POST', { content: text });
      this.setData({ inputText: '' });
      this.loadMessages();
    } catch (err) {
      wx.showToast({ title: err.message, icon: 'none' });
    }
  },

  // ==================== 让 AI 去问一件事（走协商，对方可能要先请示本人）====================
  onAskViaAI() {
    wx.showModal({
      title: '🤖 让 AI 去问',
      content: 'AI 会替你问，对方拿不准时会先跟他本人确认',
      editable: true,
      placeholderText: '想问什么？比如"明天有空吗"',
      success: (r) => {
        if (r.confirm && r.content && r.content.trim()) {
          this.doAskViaAI(r.content.trim());
        }
      }
    });
  },

  async doAskViaAI(question) {
    wx.showLoading({ title: 'AI 去问了...', mask: true });
    try {
      const res = await request('/agent-tasks/consult', 'POST', {
        friend_id: this.data.friendId,
        question: question
      });
      wx.hideLoading();

      if (res.status === 'waiting_user') {
        wx.showModal({
          title: '已转达',
          content: `${this.data.friendName} 的 AI 说得先跟他本人确认一下，稍后回你。`,
          showCancel: false,
          success: () => { this.loadMessages(); }
        });
        return;
      }

      if (res.status === 'failed') {
        wx.showModal({
          title: '没问成',
          content: res.error || '对方 AI 暂时联系不上',
          showCancel: false
        });
        return;
      }

      wx.showModal({
        title: 'AI 已经问到答复',
        content: (res.result && res.result.answer) || '对方没有回复',
        showCancel: false,
        success: () => { this.loadMessages(); }
      });
    } catch (err) {
      wx.hideLoading();
      wx.showModal({ title: '发起失败', content: err.message, showCancel: false });
    }
  },

  // ==================== 启动 AI 自主对话 ====================
  onStartAIChat() {
    wx.showModal({
      title: '🤖 让 AI 帮你聊',
      content: 'AI 会自己判断聊几轮，聊到自然结束为止',
      editable: true,
      placeholderText: '想聊什么话题？比如"周末去哪玩"',
      success: (r) => {
        if (r.confirm && r.content && r.content.trim()) {
          this.doStartAIChat(r.content.trim());
        }
      }
    });
  },

  async doStartAIChat(topic) {
    if (this.data.aiRunning) {
      wx.showToast({ title: 'AI 正在对话中，请稍候', icon: 'none' });
      return;
    }

    this.setData({ aiRunning: true });
    wx.showLoading({ title: 'AI 对话中...', mask: true });

    try {
      const res = await request('/ai-chat/start', 'POST', {
        friend_id: this.data.friendId,
        topic: topic
        // 不传 max_rounds，让 AI 自己决定
      });

      wx.hideLoading();
      this.setData({ aiRunning: false });

      // 显示总结
      const summary = res.summary || '对话完成';
      const rounds = res.current_round || 0;

      wx.showModal({
        title: `✅ AI 对话完成（${rounds} 轮）`,
        content: summary,
        showCancel: false,
        confirmText: '查看记录',
        success: () => {
          this.loadMessages();
        }
      });
    } catch (err) {
      wx.hideLoading();
      this.setData({ aiRunning: false });
      wx.showModal({
        title: '启动失败',
        content: err.message || '请稍后再试',
        showCancel: false
      });
    }
  },

  scrollToBottom() {
    setTimeout(() => {
      const msgs = this.data.messages;
      if (msgs.length > 0) {
        this.setData({ scrollToId: 'msg-' + msgs[msgs.length - 1].id });
      }
    }, 100);
  }
})