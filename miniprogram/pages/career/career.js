// pages/career/career.js
import { BASE_URL } from '../../utils/config.js';
import { getToken } from '../../utils/auth.js';
import { parseMarkdown } from '../../utils/markdown.js';

Page({
  data: {
    tab: 'optimize',
    resumeFile: null,
    jdText: '',
    company: '',
    loading: false,
    result: '',        // 保留原始文本（用于复制）
    resultNodes: []    // 渲染节点
  },

  onSwitchTab(e) {
    this.setData({ tab: e.currentTarget.dataset.tab, result: '', resultNodes: [] });
  },

  onChooseResume() {
    wx.chooseMessageFile({
      count: 1,
      type: 'file',
      extension: ['pdf', 'docx', 'txt', 'md'],
      success: (res) => {
        const f = res.tempFiles[0];
        this.setData({ resumeFile: { path: f.path, name: f.name } });
      }
    });
  },

  onJdInput(e) { this.setData({ jdText: e.detail.value }); },
  onCompanyInput(e) { this.setData({ company: e.detail.value }); },

  async onOptimize() {
    if (!this.data.resumeFile) return;
    this.setData({ loading: true });
    this._uploadAndCall('/career/optimize_resume', {});
  },

  async onMatch() {
    if (!this.data.resumeFile || !this.data.jdText) return;
    this.setData({ loading: true });
    this._uploadAndCall('/career/match_jd', { jd_text: this.data.jdText });
  },

  async onLetter() {
    if (!this.data.resumeFile || !this.data.jdText || !this.data.company) return;
    this.setData({ loading: true });
    this._uploadAndCall('/career/cover_letter', {
      jd_text: this.data.jdText,
      company: this.data.company
    });
  },

  _uploadAndCall(path, formData) {
    const token = getToken();
    wx.uploadFile({
      url: BASE_URL + path,
      filePath: this.data.resumeFile.path,
      name: 'resume',
      header: { 'Authorization': 'Bearer ' + token },
      formData: formData,
      success: (res) => {
        this.setData({ loading: false });
        try {
          const data = JSON.parse(res.data);
          if (res.statusCode === 200) {
            const raw = data.result || '';
            this.setData({
              result: raw,
              resultNodes: parseMarkdown(raw)
            });
          } else {
            wx.showToast({ title: data.detail || '处理失败', icon: 'none' });
          }
        } catch (e) {
          wx.showToast({ title: '解析失败', icon: 'none' });
        }
      },
      fail: () => {
        this.setData({ loading: false });
        wx.showToast({ title: '网络失败', icon: 'none' });
      }
    });
  },

  onCopyResult() {
    wx.setClipboardData({
      data: this.data.result,
      success: () => wx.showToast({ title: '已复制', icon: 'success' })
    });
  },

  onReset() {
    this.setData({ result: '', resultNodes: [], resumeFile: null, jdText: '', company: '' });
  }
})