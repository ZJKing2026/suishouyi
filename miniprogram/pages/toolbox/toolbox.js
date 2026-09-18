// pages/toolbox/toolbox.js
Page({
  data: {
    tools: [
      { id: 'image',     icon: '🖼',  name: '图片压缩',     desc: '压缩图片，减少体积' },
      { id: 'qrcode',    icon: '🎨',  name: '二维码生成',   desc: '文字/网址转二维码，可嵌入图片' },
      { id: 'topdf',     icon: '📄',  name: '图片转 PDF',   desc: '多张图片合并成一个 PDF' },
      { id: 'watermark', icon: '💧',  name: '图片加水印',   desc: '给图片加文字水印' },
      { id: 'pdf2img',   icon: '🖼',  name: 'PDF 转图片',   desc: '把 PDF 每页拆成图片' },
      { id: 'merge',     icon: '🧵',  name: '图片拼接长图', desc: '多张图片拼成一张长图' },
      { id: 'pdf',       icon: '📋',  name: 'PDF 合并',     desc: '多个 PDF 合并为一个' },
      { id: 'web',       icon: '🌐',  name: '网页摘要',     desc: '输入网址，AI 总结要点' },
    ]
  },

  onTapTool(e) {
    const id = e.currentTarget.dataset.id;
    wx.navigateTo({ url: `/pages/toolbox/run/run?tool=${id}` });
  }
})