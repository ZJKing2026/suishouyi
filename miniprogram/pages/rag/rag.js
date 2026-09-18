// pages/rag/rag.js
import { BASE_URL } from '../../utils/config.js';
import { getToken } from '../../utils/auth.js';
import { request } from '../../utils/request.js';

Page({
  data: {
    documents: [],
    totalChunks: 0,
    loading: false,
    uploading: false
  },

  onShow() {
    this.loadDocuments();
  },

  async loadDocuments() {
    this.setData({ loading: true });
    try {
      const res = await request('/rag/documents', 'GET');
      const docs = res.documents;
      const totalChunks = docs.reduce((sum, d) => sum + (d.chunk_count || 0), 0);
      this.setData({ documents: docs, totalChunks, loading: false });
    } catch (err) {
      console.error('加载失败:', err);
      this.setData({ loading: false });
    }
  },

  onChooseFile() {
    wx.chooseMessageFile({
      count: 1,
      type: 'file',
      extension: ['pdf', 'docx', 'txt', 'md'],
      success: (res) => {
        const f = res.tempFiles[0];
        this.doUpload(f);
      }
    });
  },

  async doUpload(file) {
    this.setData({ uploading: true });
    wx.showLoading({ title: '上传并索引中...', mask: true });

    wx.uploadFile({
      url: BASE_URL + '/rag/documents/upload',
      filePath: file.path,
      name: 'file',
      header: { 'Authorization': 'Bearer ' + getToken() },
      formData: { original_filename: file.name },
      success: (res) => {
        wx.hideLoading();
        this.setData({ uploading: false });
        try {
          const data = JSON.parse(res.data);
          if (res.statusCode === 200) {
            wx.showToast({ title: '上传成功', icon: 'success' });
            this.loadDocuments();
          } else if (res.statusCode === 428) {
            this.promptEmbeddingConfig(data.detail);
          } else {
            wx.showToast({ title: data.detail || '上传失败', icon: 'none' });
          }
        } catch (e) {
          wx.showToast({ title: '解析失败', icon: 'none' });
        }
      },
      fail: () => {
        wx.hideLoading();
        this.setData({ uploading: false });
        wx.showToast({ title: '网络失败', icon: 'none' });
      }
    });
  },

  promptEmbeddingConfig(msg) {
    wx.showModal({
      title: '需要配置知识库',
      content: msg || '请先在「设置 → API 配置」中配置 Embedding Key',
      confirmText: '去配置',
      success: (res) => {
        if (res.confirm) wx.navigateTo({ url: '/pages/setup/setup' });
      }
    });
  },

  onDeleteDoc(e) {
    const id = e.currentTarget.dataset.id;
    wx.showModal({
      title: '删除文档',
      content: '确定删除吗？',
      confirmColor: '#e74c3c',
      success: async (res) => {
        if (!res.confirm) return;
        try {
          await request(`/rag/documents/${id}`, 'DELETE');
          wx.showToast({ title: '已删除', icon: 'success' });
          this.loadDocuments();
        } catch (err) {
          wx.showToast({ title: '删除失败', icon: 'none' });
        }
      }
    });
  }
})