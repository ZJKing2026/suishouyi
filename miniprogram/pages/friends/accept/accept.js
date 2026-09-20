// pages/friends/accept/accept.js
import { request } from '../../../utils/request.js';

Page({
  data: { code: '', loading: false },

  onLoad(options) {
    if (options.code) this.setData({ code: options.code });
  },

  onInput(e) { this.setData({ code: e.detail.value.trim() }); },

  async onAccept() {
    if (!this.data.code) return;
    this.setData({ loading: true });
    try {
      await request('/friends/accept', 'POST', { invite_code: this.data.code });
      this.setData({ loading: false });
      wx.showToast({ title: '添加成功', icon: 'success' });
      setTimeout(() => {
        wx.redirectTo({ url: '/pages/friends/list/list' });
      }, 800);
    } catch (err) {
      this.setData({ loading: false });
      wx.showModal({ title: '添加失败', content: err.message, showCancel: false });
    }
  }
})