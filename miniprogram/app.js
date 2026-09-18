// app.js
import { ensureLogin } from './utils/auth.js';

App({
  globalData: {
    userInfo: null
  },

  onLaunch() {
    console.log('随手一下小程序启动了');
    // 启动时确保已登录
    this.autoLogin();
  },

  async autoLogin() {
    try {
      const { user } = await ensureLogin();
      this.globalData.userInfo = user;
      console.log('已登录:', user);
    } catch (err) {
      console.error('自动登录失败:', err);
      wx.showToast({ title: '登录失败', icon: 'none' });
    }
  }
})