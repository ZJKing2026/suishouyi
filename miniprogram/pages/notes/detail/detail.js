// pages/notes/detail/detail.js
import { request } from '../../../utils/request.js';
import { parseMarkdown } from '../../../utils/markdown.js';

Page({
  data: {
    noteId: null,
    note: null,
    summaryNodes: [],
    keyPointsNodes: [],
    showTranscript: false
  },

  onLoad(options) {
    if (options.id) {
      this.setData({ noteId: parseInt(options.id) });
      this.loadNote();
    }
  },

  async loadNote() {
    try {
      const res = await request(`/notes/${this.data.noteId}`, 'GET');
      const note = {
        ...res,
        timeLabel: this.formatFullTime(res.created_at)
      };
      this.setData({
        note,
        summaryNodes: parseMarkdown(res.summary || ''),
        keyPointsNodes: parseMarkdown(res.key_points || '')
      });
    } catch (err) {
      console.error('加载笔记失败:', err);
      wx.showToast({ title: '加载失败', icon: 'none' });
    }
  },

  formatFullTime(iso) {
    if (!iso) return '';
    const d = new Date(iso);
    return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')} ${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`;
  },

  toggleTranscript() {
    this.setData({ showTranscript: !this.data.showTranscript });
  },

  async onTitleBlur(e) {
    const newTitle = e.detail.value.trim();
    if (!newTitle || newTitle === this.data.note.title) return;

    try {
      await request(`/notes/${this.data.noteId}`, 'PUT', { title: newTitle });
      this.setData({ 'note.title': newTitle });
      wx.showToast({ title: '已保存', icon: 'success' });
    } catch (err) {
      wx.showToast({ title: '保存失败', icon: 'none' });
    }
  },

  onCopyText() {
    const { note } = this.data;
    if (!note || !note.transcript) {
      wx.showToast({ title: '没有内容', icon: 'none' });
      return;
    }
    wx.setClipboardData({
      data: note.transcript,
      success: () => wx.showToast({ title: '已复制原文', icon: 'success' })
    });
  },

  onCopyMarkdown() {
    const { note } = this.data;
    if (!note) return;

    const md = `# ${note.title}

> ${note.summary || ''}

## 关键点

${note.key_points || '（无）'}

## 原文

${note.transcript || '（无）'}

---
*由「随手一下」生成 · ${note.timeLabel}*
`;

    wx.setClipboardData({
      data: md,
      success: () => wx.showToast({ title: '已复制 Markdown', icon: 'success' })
    });
  },

  onSaveImage() {
    const { note } = this.data;
    if (!note) return;

    wx.showLoading({ title: '生成图片...' });

    const ctx = wx.createCanvasContext('noteCanvas', this);
    const W = 750;
    const H = 1000;

    ctx.setFillStyle('#ffffff');
    ctx.fillRect(0, 0, W, H);

    ctx.setFillStyle('#1a1a1a');
    ctx.fillRect(0, 0, W, 120);
    ctx.setFillStyle('#ffffff');
    ctx.setFontSize(32);
    ctx.fillText('随手一下 · 语音笔记', 40, 75);

    ctx.setFillStyle('#1a1a1a');
    ctx.setFontSize(40);
    const title = note.title || '无标题';
    const titleLines = this.wrapText(title, 20);
    let y = 200;
    titleLines.forEach(line => {
      ctx.fillText(line, 40, y);
      y += 56;
    });

    ctx.setStrokeStyle('#f0f0f0');
    ctx.setLineWidth(1);
    ctx.beginPath();
    ctx.moveTo(40, y);
    ctx.lineTo(W - 40, y);
    ctx.stroke();
    y += 40;

    if (note.summary) {
      ctx.setFillStyle('#8a8a8a');
      ctx.setFontSize(24);
      ctx.fillText('摘要', 40, y);
      y += 40;

      ctx.setFillStyle('#1a1a1a');
      ctx.setFontSize(28);
      const summaryLines = this.wrapText(note.summary, 24);
      summaryLines.forEach(line => {
        ctx.fillText(line, 40, y);
        y += 44;
      });
      y += 20;
    }

    if (note.key_points) {
      ctx.setFillStyle('#8a8a8a');
      ctx.setFontSize(24);
      ctx.fillText('关键点', 40, y);
      y += 40;

      ctx.setFillStyle('#333');
      ctx.setFontSize(26);
      const pointLines = note.key_points.split('\n');
      pointLines.forEach(line => {
        const wrapped = this.wrapText(line, 26);
        wrapped.forEach(w => {
          ctx.fillText(w, 40, y);
          y += 40;
        });
      });
    }

    ctx.setFillStyle('#b0b0b0');
    ctx.setFontSize(20);
    ctx.fillText('由「随手一下」生成', 40, H - 60);

    ctx.draw(false, () => {
      setTimeout(() => {
        wx.canvasToTempFilePath({
          canvasId: 'noteCanvas',
          success: (res) => {
            wx.hideLoading();
            wx.saveImageToPhotosAlbum({
              filePath: res.tempFilePath,
              success: () => wx.showToast({ title: '已保存到相册', icon: 'success' }),
              fail: (err) => {
                if (err.errMsg.indexOf('auth deny') !== -1) {
                  wx.showModal({
                    title: '需要相册权限',
                    content: '请在设置中开启保存到相册权限',
                    confirmText: '去设置',
                    success: (r) => {
                      if (r.confirm) wx.openSetting();
                    }
                  });
                } else {
                  wx.showToast({ title: '保存失败', icon: 'none' });
                }
              }
            });
          },
          fail: () => {
            wx.hideLoading();
            wx.showToast({ title: '生成失败', icon: 'none' });
          }
        }, this);
      }, 500);
    }, this);
  },

  wrapText(text, maxChars) {
    if (!text) return [];
    const lines = [];
    for (let i = 0; i < text.length; i += maxChars) {
      lines.push(text.slice(i, i + maxChars));
    }
    return lines;
  },

  onShareNote() {
    wx.showToast({ title: '点击右上角"···"分享', icon: 'none', duration: 2000 });
  },

  onShareAppMessage() {
    const { note } = this.data;
    return {
      title: note ? note.title : '随手一下 · 语音笔记',
      path: `/pages/notes/detail/detail?id=${this.data.noteId}`
    };
  }
})