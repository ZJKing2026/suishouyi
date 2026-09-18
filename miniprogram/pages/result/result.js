// pages/result/result.js
Page({
  data: {
    taskType: '',
    inputText: '',
    outputText: ''
  },

  onLoad(options) {
    // 从本地存储读结果（避免 URL 传长文本）
    const result = wx.getStorageSync('last_result');
    if (result) {
      this.setData({
        taskType: result.taskType || '',
        inputText: result.inputText || '',
        outputText: result.outputText || ''
      });
    }
  },

  onCopy() {
    wx.setClipboardData({
      data: this.data.outputText,
      success: () => wx.showToast({ title: '已复制', icon: 'success' })
    });
  },

  onBack() {
    wx.switchTab({ url: '/pages/index/index' });
  }
})