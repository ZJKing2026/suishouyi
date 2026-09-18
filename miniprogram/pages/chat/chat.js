// pages/chat/chat.js
import { request } from '../../utils/request.js';

Page({
  data: {
    // 抽屉
    drawerOpen: false,

    // 会话列表
    sessions: [],
    sessionId: '',
    currentTitle: 'AI 对话',

    // 消息
    messages: [],
    inputText: '',
    sending: false,
    scrollToId: ''
  },

  onLoad() {
    this.loadSessions();
  },

  onShow() {
    // 从配置页回来时刷新一下
    if (this.data.sessionId) {
      this.loadHistory();
    }
  },

  // ==================== 会话管理 ====================
  async loadSessions() {
    try {
      const res = await request('/sessions', 'GET');
      const sessions = res.sessions.map(s => ({
        ...s,
        timeLabel: this.formatTime(s.updated_at)
      }));

      // 如果没有会话，创建一个默认的
      if (sessions.length === 0) {
        const created = await request('/sessions', 'POST', { title: '新对话' });
        sessions.push({ ...created, timeLabel: '刚刚' });
        this.setData({
          sessions,
          sessionId: created.id,
          currentTitle: created.title
        });
        return;
      }

      // 否则用第一个（最新的）会话
      this.setData({
        sessions,
        sessionId: sessions[0].id,
        currentTitle: sessions[0].title
      });
      this.loadHistory();
    } catch (err) {
      console.error('加载会话失败:', err);
    }
  },

  async onNewChat() {
    try {
      const created = await request('/sessions', 'POST', { title: '新对话' });
      const newSession = { ...created, timeLabel: '刚刚' };

      this.setData({
        sessions: [newSession, ...this.data.sessions],
        sessionId: created.id,
        currentTitle: created.title,
        messages: [],
        drawerOpen: false
      });
    } catch (err) {
      wx.showToast({ title: '创建失败', icon: 'none' });
    }
  },

  onSelectSession(e) {
    const sessionId = e.currentTarget.dataset.id;
    const target = this.data.sessions.find(s => s.id === sessionId);
    if (!target) return;

    this.setData({
      sessionId,
      currentTitle: target.title,
      drawerOpen: false,
      messages: []
    });
    this.loadHistory();
  },

  onLongPressSession(e) {
    const sessionId = e.currentTarget.dataset.id;
    const target = this.data.sessions.find(s => s.id === sessionId);
    if (!target) return;

    wx.showActionSheet({
      itemList: ['重命名', '删除'],
      success: (res) => {
        if (res.tapIndex === 0) this.renameSession(sessionId, target.title);
        if (res.tapIndex === 1) this.deleteSession(sessionId);
      }
    });
  },

  renameSession(sessionId, oldTitle) {
    wx.showModal({
      title: '重命名',
      editable: true,
      placeholderText: '输入新标题',
      content: oldTitle,
      success: async (res) => {
        if (!res.confirm || !res.content.trim()) return;
        try {
          await request(`/sessions/${sessionId}`, 'PUT', { title: res.content.trim() });
          this.loadSessions();
          if (sessionId === this.data.sessionId) {
            this.setData({ currentTitle: res.content.trim() });
          }
        } catch (err) {
          wx.showToast({ title: '重命名失败', icon: 'none' });
        }
      }
    });
  },

  deleteSession(sessionId) {
    wx.showModal({
      title: '删除对话',
      content: '确定删除这个对话吗？删除后无法恢复。',
      confirmColor: '#e74c3c',
      success: async (res) => {
        if (!res.confirm) return;
        try {
          await request(`/sessions/${sessionId}`, 'DELETE');
          const remaining = this.data.sessions.filter(s => s.id !== sessionId);
          if (sessionId === this.data.sessionId) {
            // 当前会话被删，切换到第一个（或创建新的）
            if (remaining.length > 0) {
              this.setData({
                sessions: remaining,
                sessionId: remaining[0].id,
                currentTitle: remaining[0].title,
                messages: []
              });
              this.loadHistory();
            } else {
              this.loadSessions();
            }
          } else {
            this.setData({ sessions: remaining });
          }
          wx.showToast({ title: '已删除', icon: 'success' });
        } catch (err) {
          wx.showToast({ title: '删除失败', icon: 'none' });
        }
      }
    });
  },

  // ==================== 抽屉 ====================
  openDrawer() {
    this.setData({ drawerOpen: true });
  },

  closeDrawer() {
    this.setData({ drawerOpen: false });
  },

  // ==================== 抽屉底部菜单 ====================
  onTapTools() {
    this.closeDrawer();
    wx.showToast({ title: '我的工具（开发中）', icon: 'none' });
  },

  onTapPlugins() {
    this.closeDrawer();
    wx.showToast({ title: '插件（开发中）', icon: 'none' });
  },

  onTapApiConfig() {
    this.closeDrawer();
    wx.navigateTo({ url: '/pages/setup/setup' });
  },

  // ==================== 消息 ====================
  async loadHistory() {
    if (!this.data.sessionId) return;
    try {
      const res = await request(`/chat/history?session_id=${this.data.sessionId}`, 'GET');
      this.setData({ messages: res.messages });
      this.scrollToBottom();
    } catch (err) {
      console.error('加载历史失败:', err);
    }
  },

  onInput(e) {
    this.setData({ inputText: e.detail.value });
  },

  async onSend() {
    const text = this.data.inputText.trim();
    if (!text || this.data.sending) return;

    const tempUserMsg = {
      id: 'temp-' + Date.now(),
      role: 'user',
      content: text
    };
    this.setData({
      messages: this.data.messages.concat([tempUserMsg]),
      inputText: '',
      sending: true
    });
    this.scrollToBottom();

    try {
      const res = await request('/chat/send', 'POST', {
        session_id: this.data.sessionId,
        content: text
      });

      const realMessages = this.data.messages.filter(m => m.id !== tempUserMsg.id);
      realMessages.push({
        id: 'user-' + Date.now(),
        role: 'user',
        content: text
      });
      realMessages.push({
        id: res.message_id,
        role: 'assistant',
        content: res.reply
      });

      this.setData({ messages: realMessages, sending: false });
      this.scrollToBottom();

      // 刷新会话列表（标题可能更新了）
      this.loadSessions();
    } catch (err) {
      console.error('发送失败:', err);
      this.setData({ sending: false });
      wx.showToast({ title: '发送失败', icon: 'none' });
    }
  },

  scrollToBottom() {
    setTimeout(() => {
      const msgs = this.data.messages;
      if (msgs.length > 0) {
        this.setData({ scrollToId: 'msg-' + msgs[msgs.length - 1].id });
      }
    }, 100);
  },

  // ==================== 工具 ====================
  formatTime(isoString) {
    if (!isoString) return '';
    const d = new Date(isoString);
    const now = new Date();
    const diffMs = now - d;
    const diffMin = Math.floor(diffMs / 60000);

    if (diffMin < 1) return '刚刚';
    if (diffMin < 60) return `${diffMin} 分钟前`;
    const diffHour = Math.floor(diffMin / 60);
    if (diffHour < 24) return `${diffHour} 小时前`;
    const diffDay = Math.floor(diffHour / 24);
    if (diffDay < 7) return `${diffDay} 天前`;

    return `${d.getMonth() + 1}月${d.getDate()}日`;
  }
})