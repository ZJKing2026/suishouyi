// pages/profile/profile.js
import { request } from '../../utils/request.js';
import { getUser, getToken, clearAuth } from '../../utils/auth.js';
import { BASE_URL } from '../../utils/config.js';

Page({
  data: {
    userNickname: '用户',
    userInitial: '用',
    avatarUrl: '',           // 完整头像 URL（含域名）
    totalTasks: 0,
    isConfigured: false,
    apiKeyMasked: ''
  },

  onShow() {
    this.loadUserInfo();
    this.loadStats();
    this.loadConfigStatus();
  },

  // ==================== 用户信息 ====================
  loadUserInfo() {
    const user = getUser();
    if (!user) return;

    const nickname = user.nickname || '用户';
    // 把相对路径拼成完整 URL
    let avatarUrl = '';
    if (user.avatar) {
      if (user.avatar.startsWith('http')) {
        avatarUrl = user.avatar;
      } else {
        // 相对路径需要补上后端域名才能在小程序里显示
        avatarUrl = BASE_URL.replace('/api/v1', '') + user.avatar;
      }
    }

    this.setData({
      userNickname: nickname,
      userInitial: nickname.charAt(0),
      avatarUrl,
    });
  },

  // ==================== 统计 ====================
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

  // ==================== 编辑昵称 ====================
  onEditNickname() {
    wx.showModal({
      title: '修改昵称',
      editable: true,
      placeholderText: '输入新的昵称（30 字以内）',
      content: this.data.userNickname,
      success: async (r) => {
        if (!r.confirm || !r.content) return;
        const nickname = r.content.trim();
        if (!nickname) {
          wx.showToast({ title: '昵称不能为空', icon: 'none' });
          return;
        }
        if (nickname === this.data.userNickname) return;

        try {
          const res = await request('/users/me', 'PUT', { nickname });
          // 更新本地缓存
          const user = getUser() || {};
          user.nickname = res.nickname;
          wx.setStorageSync('auth_user', user);

          this.setData({
            userNickname: res.nickname,
            userInitial: res.nickname.charAt(0),
          });
          wx.showToast({ title: '昵称已更新', icon: 'success' });
        } catch (err) {
          wx.showModal({
            title: '修改失败',
            content: err.message,
            showCancel: false
          });
        }
      }
    });
  },

  // ==================== 上传头像 ====================
  onTapAvatar() {
    wx.chooseMedia({
      count: 1,
      mediaType: ['image'],
      sourceType: ['album', 'camera'],
      success: (res) => {
        const file = res.tempFiles[0];
        // 压缩
        wx.compressImage({
          src: file.tempFilePath,
          quality: 70,
          success: (c) => this.doUploadAvatar(c.tempFilePath),
          fail: () => this.doUploadAvatar(file.tempFilePath)
        });
      },
      fail: (err) => {
        if (err.errMsg && err.errMsg.indexOf('cancel') !== -1) return;
        wx.showToast({ title: '选择失败', icon: 'none' });
      }
    });
  },

  doUploadAvatar(filePath) {
    wx.showLoading({ title: '上传中...', mask: true });

    wx.uploadFile({
      url: BASE_URL + '/users/me/avatar',
      filePath: filePath,
      name: 'file',
      header: { 'Authorization': 'Bearer ' + getToken() },
      success: (res) => {
        wx.hideLoading();
        try {
          const data = JSON.parse(res.data);
          if (res.statusCode === 200) {
            // 更新本地缓存
            const user = getUser() || {};
            user.avatar = data.avatar;
            wx.setStorageSync('auth_user', user);

            const avatarUrl = BASE_URL.replace('/api/v1', '') + data.avatar;
            this.setData({ avatarUrl });
            wx.showToast({ title: '头像已更新', icon: 'success' });
          } else {
            wx.showToast({ title: data.detail || '上传失败', icon: 'none' });
          }
        } catch (e) {
          wx.showToast({ title: '解析失败', icon: 'none' });
        }
      },
      fail: () => {
        wx.hideLoading();
        wx.showToast({ title: '网络失败', icon: 'none' });
      }
    });
  },

  // ==================== 菜单 ====================
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