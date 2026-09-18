// pages/notes/list/list.js
import { request } from '../../../utils/request.js';

Page({
  data: {
    notes: [],
    loading: true
  },

  onShow() {
    this.loadNotes();
  },

  onPullDownRefresh() {
    this.loadNotes().then(() => wx.stopPullDownRefresh());
  },

  async loadNotes() {
    this.setData({ loading: true });
    try {
      const res = await request('/notes', 'GET');
      const notes = res.notes.map(n => ({
        ...n,
        timeLabel: this.formatTime(n.created_at)
      }));
      this.setData({ notes, loading: false });
    } catch (err) {
      console.error('加载笔记失败:', err);
      this.setData({ loading: false });
      wx.showToast({ title: '加载失败', icon: 'none' });
    }
  },

  onTapNote(e) {
    const id = e.currentTarget.dataset.id;
    wx.navigateTo({ url: `/pages/notes/detail/detail?id=${id}` });
  },

  onLongPressNote(e) {
    const id = e.currentTarget.dataset.id;
    wx.showActionSheet({
      itemList: ['删除'],
      itemColor: '#e74c3c',
      success: (res) => {
        if (res.tapIndex === 0) this.confirmDelete(id);
      }
    });
  },

  confirmDelete(id) {
    wx.showModal({
      title: '删除笔记',
      content: '确定删除这条笔记吗？',
      confirmColor: '#e74c3c',
      success: async (res) => {
        if (!res.confirm) return;
        try {
          await request(`/notes/${id}`, 'DELETE');
          wx.showToast({ title: '已删除', icon: 'success' });
          this.loadNotes();
        } catch (err) {
          wx.showToast({ title: '删除失败', icon: 'none' });
        }
      }
    });
  },

  onTapRecord() {
    wx.navigateTo({ url: '/pages/notes/record/record' });
  },

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