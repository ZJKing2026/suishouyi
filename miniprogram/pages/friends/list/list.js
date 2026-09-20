// pages/friends/list/list.js
import { request } from '../../../utils/request.js';

Page({
  data: {
    friends: [],
    loading: true,
    inviteCode: ''      // 缓存最近生成的邀请码，用于分享
  },

  onShow() {
    this.loadFriends();
  },

  onPullDownRefresh() {
    this.loadFriends().then(() => wx.stopPullDownRefresh());
  },

  // ==================== 加载好友列表 ====================
  async loadFriends() {
    this.setData({ loading: true });
    try {
      const res = await request('/friends', 'GET');
      this.setData({ friends: res.friends, loading: false });
    } catch (err) {
      console.error('加载好友失败:', err);
      this.setData({ loading: false });
    }
  },

  // ==================== 生成邀请码 ====================
  async onInvite() {
    wx.showLoading({ title: '生成中...', mask: true });
    try {
      const res = await request('/friends/invite', 'POST');
      wx.hideLoading();

      const code = res.invite_code;
      this.setData({ inviteCode: code });

      // 复制到剪贴板
      wx.setClipboardData({
        data: code,
        success: () => {
          wx.showModal({
            title: '邀请码已复制',
            content: `邀请码：${code}\n\n已经复制到剪贴板。\n请打开微信聊天窗口，粘贴发给好友。`,
            confirmText: '知道了',
            showCancel: false
          });
        },
        fail: () => {
          wx.showModal({
            title: '邀请码',
            content: `邀请码：${code}\n\n请手动复制发给好友`,
            showCancel: false
          });
        }
      });
    } catch (err) {
      wx.hideLoading();
      console.error('生成邀请码失败:', err);
      wx.showModal({
        title: '生成失败',
        content: err.message || '请稍后再试',
        showCancel: false
      });
    }
  },

  // ==================== 去"输入邀请码"页 ====================
  onGoAccept() {
    wx.navigateTo({ url: '/pages/friends/accept/accept' });
  },

  // ==================== 点击好友 → 进入对话 ====================
  onTapFriend(e) {
    const { id, name } = e.currentTarget.dataset;
    wx.navigateTo({
      url: `/pages/friends/chat/chat?friend_id=${id}&name=${encodeURIComponent(name)}`
    });
  },

  // ==================== 分享给微信好友（右上角"···"转发） ====================
  onShareAppMessage() {
    if (this.data.inviteCode) {
      return {
        title: '加我为好友，让 AI 帮我们传话',
        path: `/pages/friends/accept/accept?code=${this.data.inviteCode}`
      };
    }
    return {
      title: '加我为好友，让 AI 帮我们传话',
      path: '/pages/friends/accept/accept'
    };
  }
})