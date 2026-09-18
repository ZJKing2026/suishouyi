// pages/tools/import/import.js
import { request } from '../../../utils/request.js';

const DEMO_URL = 'https://petstore3.swagger.io/api/v3/openapi.json';

Page({
  data: {
    step: 'choose',
    method: '',
    showIntro: false,

    urlContent: '',
    jsonContent: '',
    prefix: '',

    parsing: false,
    parsedTools: [],
    parsedToolsPreview: [],
    importing: false
  },

  toggleIntro() {
    this.setData({ showIntro: !this.data.showIntro });
  },

  onPickDemo() {
    this.setData({ step: 'fill', method: 'demo' });
  },

  onPickUrl() {
    this.setData({ step: 'fill', method: 'url' });
  },

  onPickText() {
    this.setData({ step: 'fill', method: 'text' });
  },

  onBackToChoose() {
    this.setData({
      step: 'choose',
      method: '',
      urlContent: '',
      jsonContent: '',
      prefix: '',
      parsedTools: [],
      parsedToolsPreview: [],
      showIntro: false
    });
  },

  onUrlInput(e) { this.setData({ urlContent: e.detail.value }); },
  onJsonInput(e) { this.setData({ jsonContent: e.detail.value }); },

  onPrefixInput(e) {
    this.setData({ prefix: e.detail.value });
    const preview = this.data.parsedTools.slice(0, 5).map(t => ({ ...t }));
    this.setData({ parsedToolsPreview: preview });
  },

  onParseDemo() {
    this.setData({ parsing: true });
    this.doParse('url', DEMO_URL);
  },

  onParseUrl() {
    if (!this.data.urlContent.trim()) return;
    this.setData({ parsing: true });
    this.doParse('url', this.data.urlContent.trim());
  },

  onParseText() {
    if (!this.data.jsonContent.trim()) return;
    this.setData({ parsing: true });
    this.doParse('text', this.data.jsonContent.trim());
  },

  async doParse(sourceType, content) {
    try {
      const res = await request('/openapi/parse', 'POST', {
        source_type: sourceType,
        content: content
      });

      if (res.success && res.tools && res.tools.length > 0) {
        this.setData({
          step: 'preview',
          parsing: false,
          parsedTools: res.tools,
          parsedToolsPreview: res.tools.slice(0, 5)
        });
      } else {
        this.setData({ parsing: false });
        wx.showModal({
          title: '解析失败',
          content: res.message || '没有找到任何接口',
          showCancel: false
        });
      }
    } catch (err) {
      this.setData({ parsing: false });
      wx.showModal({
        title: '解析失败',
        content: this._friendlyError(err.message),
        showCancel: false
      });
    }
  },

  _friendlyError(msg) {
    if (!msg) return '未知错误，请重试';
    if (msg.indexOf('404') !== -1) return '这个网址找不到，检查一下有没有输错';
    if (msg.indexOf('下载超时') !== -1) return '网址打开太慢，稍后再试';
    if (msg.indexOf('JSON') !== -1) return '文档格式不对，可能需要换一个网址';
    if (msg.indexOf('不是有效') !== -1) return '这不是 OpenAPI 文档，检查一下网址';
    return msg;
  },

  async onImport() {
    if (this.data.parsedTools.length === 0) return;

    this.setData({ importing: true });

    try {
      const res = await request('/openapi/import', 'POST', {
        tools: this.data.parsedTools,
        prefix: this.data.prefix.trim()
      });

      this.setData({ importing: false });

      wx.showModal({
        title: '🎉 导入成功',
        content: `已添加 ${res.created} 个工具。回到对话页，让 AI 试试吧！`,
        showCancel: false,
        confirmText: '去看看',
        success: () => {
          wx.navigateBack();
        }
      });
    } catch (err) {
      this.setData({ importing: false });
      wx.showModal({
        title: '导入失败',
        content: err.message,
        showCancel: false
      });
    }
  }
})