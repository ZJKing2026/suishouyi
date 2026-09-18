// pages/profile/profile.js
import { request } from '../../utils/request.js';
import { getUser, clearAuth } from '../../utils/auth.js';

Page({
  data: {
    userNickname: '用户',
    userInitial: '用',
    totalTasks: 0,
    isConfigured: false,
    apiKeyMasked: ''
  },

  onShow() {
    this.loadUserInfo();
    this.loadStats();
    this.loadConfigStatus();
  },

  loadUserInfo() {
    const user = getUser();
    if (user) {
      const nickname = user.nickname || '用户';
      this.setData({
        userNickname: nickname,
        userInitial: nickname.charAt(0)
      });
    }
  },

  async loadStats() {
    try {
      const res = await request('/tasks?limit=1', 'GET');
      this.setData({ totalTasks: res.total });
    } catch (err) {
      console.error('获取统计失败:', err);
    }
  },

  async loadConfigStatus() {
    try {
      const res = await request('/user/config', 'GET');
      this.setData({
        isConfigured: res.is_configured,
        apiKeyMasked: res.llm_api_key_masked || ''
      });
    } catch (err) {
      console.error('加载配置状态失败:', err);
    }
  },

  onTapTools() {
    wx.navigateTo({ url: '/pages/tools/tools' });
  },

  onTapApiConfig() {
    wx.navigateTo({ url: '/pages/setup/setup' });
  },

  onTapAbout() {
    wx.navigateTo({ url: '/pages/about/about' });
  },

  onLogout() {
    wx.showModal({
      title: '退出登录',
      content: '确定退出当前账号吗？',
      success: (res) => {
        if (res.confirm) {
          clearAuth();
          wx.showToast({ title: '已退出', icon: 'success' });
          setTimeout(() => {
            wx.reLaunch({ url: '/pages/index/index' });
          }, 800);
        }
      }
    });
  }
})