// pages/groups/list/list.js
import { request } from '../../../utils/request.js';

Page({
  data: { groups: [], loading: true },

  onShow() { this.loadGroups(); },

  async loadGroups() {
    try {
      const res = await request('/groups', 'GET');
      this.setData({ groups: res.groups, loading: false });
    } catch (err) {
      console.error(err);
      this.setData({ loading: false });
    }
  },

  onCreate() {
    wx.showModal({
      title: '创建群聊',
      editable: true,
      placeholderText: '群名称',
      success: async (r) => {
        if (!r.confirm || !r.content) return;
        try {
          const res = await request('/friends', 'GET');
          if (res.friends.length === 0) {
            wx.showToast({ title: '先加好友', icon: 'none' });
            return;
          }
          const memberIds = res.friends.map(f => f.friend_id);
          await request('/groups', 'POST', { name: r.content, member_ids: memberIds });
          wx.showToast({ title: '创建成功', icon: 'success' });
          this.loadGroups();
        } catch (err) {
          wx.showModal({ title: '失败', content: err.message, showCancel: false });
        }
      }
    });
  },

  onTapGroup(e) {
    wx.navigateTo({ url: `/pages/groups/detail/detail?id=${e.currentTarget.dataset.id}` });
  }
})