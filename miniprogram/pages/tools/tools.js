// pages/tools/tools.js
import { request } from '../../utils/request.js';

Page({
  data: {
    activeTab: 'mine',
    myTools: [],
    loading: true,
    marketTools: [],
    marketLoading: false,
    marketLoaded: false
  },

  onShow() {
    this.loadMyTools();
    if (this.data.marketLoaded) this.loadMarket();
  },

  onSwitchTab(e) {
    const tab = e.currentTarget.dataset.tab;
    this.setData({ activeTab: tab });
    if (tab === 'market' && !this.data.marketLoaded) this.loadMarket();
  },

  async loadMyTools() {
    this.setData({ loading: true });
    try {
      const res = await request('/tools', 'GET');
      this.setData({ myTools: res.tools, loading: false });
    } catch (err) {
      console.error('加载工具失败:', err);
      this.setData({ loading: false });
    }
  },

  async loadMarket() {
    this.setData({ marketLoading: true });
    try {
      const res = await request('/market/tools', 'GET');
      const addedNames = res.added_names || [];
      const tools = res.tools.map(t => ({ ...t, added: addedNames.includes(t.name) }));
      this.setData({ marketTools: tools, marketLoading: false, marketLoaded: true });
    } catch (err) {
      console.error('加载市场失败:', err);
      this.setData({ marketLoading: false });
    }
  },

  async onAddTool(e) {
    const id = e.currentTarget.dataset.id;
    const added = e.currentTarget.dataset.added;
    if (added) {
      wx.showToast({ title: '已添加过', icon: 'none' });
      return;
    }
    try {
      await request(`/market/tools/${id}/add`, 'POST');
      wx.showToast({ title: '添加成功', icon: 'success' });
      const tools = this.data.marketTools.map(t =>
        t.id === id ? { ...t, added: true } : t
      );
      this.setData({ marketTools: tools });
      this.loadMyTools();
    } catch (err) {
      wx.showModal({ title: '添加失败', content: err.message, showCancel: false });
    }
  },

  onTapImport() {
    wx.navigateTo({ url: '/pages/tools/import/import' });
  },

  onTapCreate() {
    wx.navigateTo({ url: '/pages/tools/edit/edit' });
  },

  onLongPressTool(e) {
    const id = e.currentTarget.dataset.id;
    wx.showModal({
      title: '删除工具',
      content: '确定删除这个工具吗？',
      confirmColor: '#e74c3c',
      success: async (res) => {
        if (!res.confirm) return;
        try {
          await request(`/tools/${id}`, 'DELETE');
          wx.showToast({ title: '已删除', icon: 'success' });
          this.loadMyTools();
        } catch (err) {
          wx.showToast({ title: '删除失败', icon: 'none' });
        }
      }
    });
  }
})