// pages/toolbox/run/run.js
import { BASE_URL } from '../../../utils/config.js';
import { getToken } from '../../../utils/auth.js';

const CONFIGS = {
  image:     { title: '图片压缩',     desc: '减小图片体积，方便分享' },
  qrcode:    { title: '二维码生成',   desc: '文字/网址转二维码，可嵌入图片' },
  topdf:     { title: '图片转 PDF',   desc: '多张图片合并成一个 PDF' },
  watermark: { title: '图片加水印',   desc: '给图片加文字水印' },
  pdf2img:   { title: 'PDF 转图片',   desc: '把 PDF 每页拆成图片' },
  merge:     { title: '图片拼接长图', desc: '多张图片拼成一张' },
  pdf:       { title: 'PDF 合并',     desc: '多个 PDF 合并' },
  web:       { title: '网页摘要',     desc: 'AI 总结网页核心要点' },
};

Page({
  data: {
    tool: '',
    config: {},
    loading: false,
    result: null,
    imgBaseUrl: BASE_URL.replace('/api/v1', ''),

    // 图片压缩
    pickedFile: null,
    quality: 70,

    // 二维码
    qrText: '',
    logoFile: null,

    // 图片转 PDF
    pdfImages: [],

    // 加水印
    watermarkText: '',
    watermarkPos: 'br',
    watermarkOpacity: 80,

    // PDF 转图片
    pdfFile: null,

    // 拼接长图
    mergeImages: [],
    mergeDirection: 'vertical',

    // PDF 合并
    pdfFiles: [],

    // 网页摘要
    webUrl: '',
  },

  onLoad(options) {
    const tool = options.tool || 'image';
    this.setData({
      tool,
      config: CONFIGS[tool] || CONFIGS.image
    });
    wx.setNavigationBarTitle({ title: (CONFIGS[tool] || {}).title || '工具' });
  },

  // ==================== 图片压缩 ====================
  onChooseImage() {
    wx.chooseMedia({
      count: 1,
      mediaType: ['image'],
      sourceType: ['album', 'camera'],
      success: (res) => {
        const file = res.tempFiles[0];
        this.setData({
          pickedFile: {
            path: file.tempFilePath,
            name: file.tempFilePath.split('/').pop() || 'image.jpg'
          }
        });
      }
    });
  },

  onQualityChange(e) {
    this.setData({ quality: e.detail.value });
  },

  async onSubmitImage() {
    const { pickedFile, quality } = this.data;
    if (!pickedFile) return;

    this.setData({ loading: true });

    wx.uploadFile({
      url: BASE_URL + '/ext/image/compress',
      filePath: pickedFile.path,
      name: 'file',
      header: { 'Authorization': 'Bearer ' + getToken() },
      formData: { quality: String(quality) },
      success: (res) => {
        try {
          const data = JSON.parse(res.data);
          if (res.statusCode >= 200 && res.statusCode < 300) {
            this.setData({ loading: false, result: { type: 'image', ...data } });
          } else {
            this.setData({ loading: false });
            wx.showToast({ title: data.detail || '压缩失败', icon: 'none' });
          }
        } catch (e) {
          this.setData({ loading: false });
          wx.showToast({ title: '解析失败', icon: 'none' });
        }
      },
      fail: () => {
        this.setData({ loading: false });
        wx.showToast({ title: '网络失败', icon: 'none' });
      }
    });
  },

  // ==================== 保存图片 ====================
  onSaveImage() {
    const url = this.data.imgBaseUrl + this.data.result.url;
    wx.showLoading({ title: '下载中...' });
    wx.downloadFile({
      url,
      success: (res) => {
        wx.hideLoading();
        wx.saveImageToPhotosAlbum({
          filePath: res.tempFilePath,
          success: () => wx.showToast({ title: '已保存', icon: 'success' }),
          fail: () => wx.showToast({ title: '保存失败', icon: 'none' })
        });
      },
      fail: () => {
        wx.hideLoading();
        wx.showToast({ title: '下载失败', icon: 'none' });
      }
    });
  },

  // ==================== 二维码 ====================
  onQrTextInput(e) { this.setData({ qrText: e.detail.value }); },

  onChooseLogo() {
    wx.chooseMedia({
      count: 1,
      mediaType: ['image'],
      sourceType: ['album', 'camera'],
      success: (res) => {
        this.setData({ logoFile: { path: res.tempFiles[0].tempFilePath } });
      }
    });
  },

  async onSubmitQrcode() {
    const { qrText, logoFile } = this.data;
    if (!qrText) return;

    this.setData({ loading: true });

    if (logoFile) {
      wx.uploadFile({
        url: BASE_URL + '/ext/qrcode',
        filePath: logoFile.path,
        name: 'logo',
        header: { 'Authorization': 'Bearer ' + getToken() },
        formData: { text: qrText, size: '400' },
        success: (res) => {
          try {
            const data = JSON.parse(res.data);
            if (res.statusCode === 200) {
              this.setData({ loading: false, result: { type: 'image', ...data } });
            } else {
              this.setData({ loading: false });
              wx.showToast({ title: data.detail || '生成失败', icon: 'none' });
            }
          } catch (e) {
            this.setData({ loading: false });
            wx.showToast({ title: '解析失败', icon: 'none' });
          }
        },
        fail: () => {
          this.setData({ loading: false });
          wx.showToast({ title: '网络失败', icon: 'none' });
        }
      });
    } else {
      wx.request({
        url: BASE_URL + '/ext/qrcode',
        method: 'POST',
        header: {
          'Content-Type': 'application/x-www-form-urlencoded',
          'Authorization': 'Bearer ' + getToken()
        },
        data: { text: qrText, size: 400 },
        success: (res) => {
          if (res.statusCode === 200) {
            this.setData({ loading: false, result: { type: 'image', ...res.data } });
          } else {
            this.setData({ loading: false });
            wx.showToast({ title: res.data.detail || '生成失败', icon: 'none' });
          }
        },
        fail: () => {
          this.setData({ loading: false });
          wx.showToast({ title: '网络失败', icon: 'none' });
        }
      });
    }
  },

  // ==================== 图片转 PDF ====================
  onChooseImagesForPdf() {
    wx.chooseMedia({
      count: 9,
      mediaType: ['image'],
      sourceType: ['album', 'camera'],
      success: (res) => {
        const files = res.tempFiles.map(f => ({
          path: f.tempFilePath,
          name: f.tempFilePath.split('/').pop() || 'image.jpg'
        }));
        this.setData({ pdfImages: files });
      }
    });
  },

  async onSubmitToPdf() {
    const { pdfImages } = this.data;
    if (pdfImages.length === 0) return;

    this.setData({ loading: true });

    wx.uploadFile({
      url: BASE_URL + '/ext/image/to_pdf',
      filePath: pdfImages[0].path,
      name: 'files',
      header: { 'Authorization': 'Bearer ' + getToken() },
      success: (res) => {
        try {
          const data = JSON.parse(res.data);
          if (res.statusCode === 200) {
            this.setData({ loading: false, result: { type: 'pdf', ...data } });
          } else {
            this.setData({ loading: false });
            wx.showToast({ title: data.detail || '生成失败', icon: 'none' });
          }
        } catch (e) {
          this.setData({ loading: false });
          wx.showToast({ title: '解析失败', icon: 'none' });
        }
      },
      fail: () => {
        this.setData({ loading: false });
        wx.showToast({ title: '网络失败', icon: 'none' });
      }
    });
  },

  // ==================== 图片加水印 ====================
  onWatermarkTextInput(e) { this.setData({ watermarkText: e.detail.value }); },
  onPositionChange(e) { this.setData({ watermarkPos: e.currentTarget.dataset.pos }); },
  onOpacityChange(e) { this.setData({ watermarkOpacity: e.detail.value }); },

  async onSubmitWatermark() {
    const { pickedFile, watermarkText, watermarkPos, watermarkOpacity } = this.data;
    if (!pickedFile || !watermarkText) return;

    this.setData({ loading: true });

    wx.uploadFile({
      url: BASE_URL + '/ext/image/watermark',
      filePath: pickedFile.path,
      name: 'file',
      header: { 'Authorization': 'Bearer ' + getToken() },
      formData: {
        text: watermarkText,
        position: watermarkPos,
        opacity: String(watermarkOpacity)
      },
      success: (res) => {
        try {
          const data = JSON.parse(res.data);
          if (res.statusCode === 200) {
            this.setData({ loading: false, result: { type: 'image', ...data } });
          } else {
            this.setData({ loading: false });
            wx.showToast({ title: data.detail || '添加失败', icon: 'none' });
          }
        } catch (e) {
          this.setData({ loading: false });
          wx.showToast({ title: '解析失败', icon: 'none' });
        }
      },
      fail: () => {
        this.setData({ loading: false });
        wx.showToast({ title: '网络失败', icon: 'none' });
      }
    });
  },

  // ==================== PDF 转图片 ====================
  onChoosePdfFile() {
    wx.chooseMessageFile({
      count: 1,
      type: 'file',
      extension: ['pdf'],
      success: (res) => {
        const f = res.tempFiles[0];
        this.setData({ pdfFile: { path: f.path, name: f.name } });
      }
    });
  },

  async onSubmitPdfToImg() {
    const { pdfFile } = this.data;
    if (!pdfFile) return;

    this.setData({ loading: true });

    wx.uploadFile({
      url: BASE_URL + '/ext/pdf/to_images',
      filePath: pdfFile.path,
      name: 'file',
      header: { 'Authorization': 'Bearer ' + getToken() },
      formData: { max_pages: '20' },
      success: (res) => {
        try {
          const data = JSON.parse(res.data);
          if (res.statusCode === 200) {
            this.setData({ loading: false, result: { type: 'images', ...data } });
          } else {
            this.setData({ loading: false });
            wx.showToast({ title: data.detail || '转换失败', icon: 'none' });
          }
        } catch (e) {
          this.setData({ loading: false });
          wx.showToast({ title: '解析失败', icon: 'none' });
        }
      },
      fail: () => {
        this.setData({ loading: false });
        wx.showToast({ title: '网络失败', icon: 'none' });
      }
    });
  },

  // ==================== 图片拼接长图 ====================
  onChooseImagesForMerge() {
    wx.chooseMedia({
      count: 10,
      mediaType: ['image'],
      sourceType: ['album', 'camera'],
      success: (res) => {
        const files = res.tempFiles.map(f => ({
          path: f.tempFilePath,
          name: f.tempFilePath.split('/').pop() || 'image.jpg'
        }));
        this.setData({ mergeImages: files });
      }
    });
  },

  onDirectionChange(e) {
    this.setData({ mergeDirection: e.currentTarget.dataset.dir });
  },

  async onSubmitMerge() {
    const { mergeImages, mergeDirection } = this.data;
    if (mergeImages.length < 2) return;

    this.setData({ loading: true });
    wx.showLoading({ title: '处理中...', mask: true });

    try {
      const base64List = [];
      for (const file of mergeImages) {
        const b64 = await this._fileToBase64(file.path);
        base64List.push(b64);
      }

      wx.request({
        url: BASE_URL + '/ext/image/merge',
        method: 'POST',
        header: {
          'Content-Type': 'application/json',
          'Authorization': 'Bearer ' + getToken()
        },
        data: {
          images: base64List,
          direction: mergeDirection
        },
        success: (res) => {
          wx.hideLoading();
          if (res.statusCode === 200) {
            this.setData({ loading: false, result: { type: 'image', ...res.data } });
          } else {
            this.setData({ loading: false });
            wx.showToast({ title: res.data.detail || '拼接失败', icon: 'none' });
          }
        },
        fail: () => {
          wx.hideLoading();
          this.setData({ loading: false });
          wx.showToast({ title: '网络失败', icon: 'none' });
        }
      });
    } catch (err) {
      wx.hideLoading();
      this.setData({ loading: false });
      wx.showToast({ title: '读取图片失败', icon: 'none' });
    }
  },

  // ==================== PDF 合并（base64） ====================
  onChoosePdf() {
    wx.chooseMessageFile({
      count: 10,
      type: 'file',
      extension: ['pdf'],
      success: (res) => {
        const files = res.tempFiles.map(f => ({ path: f.path, name: f.name }));
        this.setData({ pdfFiles: files });
      }
    });
  },

  async onSubmitPdfMerge() {
    const { pdfFiles } = this.data;
    if (pdfFiles.length < 2) return;

    this.setData({ loading: true });
    wx.showLoading({ title: '读取文件...', mask: true });

    try {
      const filesData = [];
      for (const file of pdfFiles) {
        const b64 = await this._fileToBase64(file.path);
        filesData.push({ name: file.name, content: b64 });
      }

      wx.hideLoading();
      wx.showLoading({ title: '合并中...', mask: true });

      wx.request({
        url: BASE_URL + '/ext/pdf/merge_base64',
        method: 'POST',
        header: {
          'Content-Type': 'application/json',
          'Authorization': 'Bearer ' + getToken()
        },
        data: { files: filesData },
        success: (res) => {
          wx.hideLoading();
          if (res.statusCode === 200) {
            this.setData({ loading: false, result: { type: 'pdf', ...res.data } });
          } else {
            this.setData({ loading: false });
            wx.showToast({ title: res.data.detail || '合并失败', icon: 'none' });
          }
        },
        fail: () => {
          wx.hideLoading();
          this.setData({ loading: false });
          wx.showToast({ title: '网络失败', icon: 'none' });
        }
      });
    } catch (err) {
      wx.hideLoading();
      this.setData({ loading: false });
      wx.showToast({ title: '读取文件失败', icon: 'none' });
    }
  },

  // ==================== 网页摘要 ====================
  onWebUrlInput(e) { this.setData({ webUrl: e.detail.value }); },

  async onSubmitWeb() {
    const { webUrl } = this.data;
    if (!webUrl) return;

    this.setData({ loading: true });

    wx.request({
      url: BASE_URL + '/ext/web/summary',
      method: 'POST',
      header: {
        'Content-Type': 'application/x-www-form-urlencoded',
        'Authorization': 'Bearer ' + getToken()
      },
      data: { url: webUrl },
      success: (res) => {
        if (res.statusCode === 200) {
          this.setData({ loading: false, result: { type: 'text', text: res.data.summary } });
        } else {
          this.setData({ loading: false });
          wx.showToast({ title: res.data.detail || '摘要失败', icon: 'none' });
        }
      },
      fail: () => {
        this.setData({ loading: false });
        wx.showToast({ title: '网络失败', icon: 'none' });
      }
    });
  },

  // ==================== 通用 ====================
  onCopyText() {
    wx.setClipboardData({
      data: this.data.result.text,
      success: () => wx.showToast({ title: '已复制', icon: 'success' })
    });
  },

  onCopyPdfUrl() {
    const url = this.data.imgBaseUrl + this.data.result.url;
    wx.setClipboardData({
      data: url,
      success: () => wx.showToast({ title: '链接已复制', icon: 'success' })
    });
  },

  onReset() {
    this.setData({
      result: null,
      pickedFile: null,
      qrText: '',
      logoFile: null,
      pdfImages: [],
      watermarkText: '',
      watermarkPos: 'br',
      watermarkOpacity: 80,
      pdfFile: null,
      mergeImages: [],
      mergeDirection: 'vertical',
      pdfFiles: [],
      webUrl: ''
    });
  },

  // ==================== 内部工具 ====================
  _fileToBase64(filePath) {
    return new Promise((resolve, reject) => {
      const fs = wx.getFileSystemManager();
      fs.readFile({
        filePath,
        encoding: 'base64',
        success: (res) => resolve(res.data),
        fail: reject
      });
    });
  }
})