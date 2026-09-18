// pages/mcp/mcp.js
import { request } from '../../utils/request.js';

Page({
  data: {
    servers: [],
    loading: true,
    showIntro: false,

    // 添加弹窗
    modalOpen: false,
    formName: '',
    formUrl: '',
    formToken: '',
    creating: false,

    // 详情弹窗
    detailOpen: false,
    detailServer: { name: '', url: '', tools: [] }
  },

  onShow() {
    this.loadServers();
  },

  toggleIntro() {
    this.setData({ showIntro: !this.data.showIntro });
  },

  async loadServers() {
    this.setData({ loading: true });
    try {
      const res = await request('/mcp/servers', 'GET');
      this.setData({ servers: res.servers, loading: false });
    } catch (err) {
      console.error('加载失败:', err);
      this.setData({ loading: false });
    }
  },

  onTapCreate() {
    this.setData({
      modalOpen: true,
      formName: '',
      formUrl: '',
      formToken: ''
    });
  },

  closeModal() {
    this.setData({ modalOpen: false });
  },

  onNameInput(e) { this.setData({ formName: e.detail.value }); },
  onUrlInput(e) { this.setData({ formUrl: e.detail.value }); },
  onTokenInput(e) { this.setData({ formToken: e.detail.value }); },

  async confirmCreate() {
    const { formName, formUrl, formToken } = this.data;

    if (!formName.trim()) { wx.showToast({ title: '请填名称', icon: 'none' }); return; }
    if (!formUrl.trim() || !/^https?:\/\//.test(formUrl)) {
      wx.showToast({ title: 'URL 必须以 http(s):// 开头', icon: 'none' });
      return;
    }

    this.setData({ creating: true });

    try {
      await request('/mcp/servers', 'POST', {
        name: formName.trim(),
        url: formUrl.trim(),
        auth_token: formToken.trim()
      });
      wx.showToast({ title: '添加成功', icon: 'success' });
      this.setData({ modalOpen: false, creating: false });
      this.loadServers();
    } catch (err) {
      this.setData({ creating: false });
      wx.showModal({
        title: '添加失败',
        content: err.message,
        showCancel: false
      });
    }
  },

  onTapDetail(e) {
    const id = e.currentTarget.dataset.id;
    const server = this.data.servers.find(s => s.id === id);
    if (!server) return;
    this.setData({ detailOpen: true, detailServer: server });
  },

  closeDetail() {
    this.setData({ detailOpen: false });
  },

  async onRefresh(e) {
    const id = e.currentTarget.dataset.id;
    wx.showLoading({ title: '刷新中...', mask: true });
    try {
      await request(`/mcp/servers/${id}/refresh`, 'POST');
      wx.hideLoading();
      wx.showToast({ title: '已刷新', icon: 'success' });
      this.loadServers();
    } catch (err) {
      wx.hideLoading();
      wx.showToast({ title: '刷新失败', icon: 'none' });
    }
  },

  onLongPressServer(e) {
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
      title: '删除 MCP 服务器',
      content: '删除后 AI 将不再使用它的工具',
      confirmColor: '#e74c3c',
      success: async (res) => {
        if (!res.confirm) return;
        try {
          await request(`/mcp/servers/${id}`, 'DELETE');
          wx.showToast({ title: '已删除', icon: 'success' });
          this.loadServers();
        } catch (err) {
          wx.showToast({ title: '删除失败', icon: 'none' });
        }
      }
    });
  }
})