// pages/setup/setup.js
import { request } from '../../utils/request.js';
import { PROVIDERS } from '../../utils/providers.js';

Page({
  data: {
    providers: PROVIDERS,
    providerIndex: 0,

    // 文本
    apiKey: '',
    baseUrl: 'https://api.deepseek.com/v1',
    llmModel: 'deepseek-chat',

    // 视觉
    useSameForVision: true,
    visionProviderIndex: 0,
    visionApiKey: '',
    visionBaseUrl: 'https://api.deepseek.com/v1',
    visionModel: '',

    // Embedding（知识库）
    embeddingApiKey: '',
    embeddingBaseUrl: 'https://api.siliconflow.cn/v1',
    embeddingModel: 'BAAI/bge-m3',
    embeddingVerifying: false,
    embeddingVerified: false,
    embeddingMsg: '',
    embeddingError: '',

    // UI 状态
    verifying: false,
    saving: false,
    verified: false,
    verifyMsg: '',
    verifyError: ''
  },

  onLoad() {
    this.loadExistingConfig();
  },

  async loadExistingConfig() {
    try {
      const res = await request('/user/config', 'GET');
      if (res.llm_base_url) {
        const idx = PROVIDERS.findIndex(p => p.baseUrl === res.llm_base_url);
        this.setData({
          providerIndex: idx >= 0 ? idx : PROVIDERS.length - 1,
          baseUrl: res.llm_base_url,
          llmModel: res.llm_model,
          visionModel: res.vision_model,
          verified: res.is_configured,
          useSameForVision: !res.vision_api_key_masked,
          embeddingBaseUrl: res.embedding_base_url || 'https://api.siliconflow.cn/v1',
          embeddingModel: res.embedding_model || 'BAAI/bge-m3',
          embeddingVerified: res.is_embedding_configured
        });
      }
    } catch (err) {
      console.error('加载配置失败:', err);
    }
  },

  // ========== 文本 AI ==========
  onProviderChange(e) {
    const idx = parseInt(e.detail.value);
    const p = PROVIDERS[idx];
    this.setData({
      providerIndex: idx,
      baseUrl: p.baseUrl || this.data.baseUrl,
      llmModel: p.llmModel || this.data.llmModel,
      visionModel: p.visionModel || this.data.visionModel,
      verified: false, verifyMsg: '', verifyError: ''
    });
  },

  onVisionProviderChange(e) {
    const idx = parseInt(e.detail.value);
    const p = PROVIDERS[idx];
    this.setData({
      visionProviderIndex: idx,
      visionBaseUrl: p.baseUrl || this.data.visionBaseUrl,
      visionModel: p.visionModel || this.data.visionModel
    });
  },

  onKeyInput(e) { this.setData({ apiKey: e.detail.value, verified: false, verifyMsg: '', verifyError: '' }); },
  onBaseUrlInput(e) { this.setData({ baseUrl: e.detail.value }); },
  onModelInput(e) { this.setData({ llmModel: e.detail.value }); },
  onVisionKeyInput(e) { this.setData({ visionApiKey: e.detail.value }); },
  onVisionBaseUrlInput(e) { this.setData({ visionBaseUrl: e.detail.value }); },
  onVisionModelInput(e) { this.setData({ visionModel: e.detail.value }); },
  onToggleSameVision(e) { this.setData({ useSameForVision: e.detail.value }); },

  // ========== Embedding ==========
  onEmbeddingKeyInput(e) {
    this.setData({
      embeddingApiKey: e.detail.value,
      embeddingVerified: false,
      embeddingMsg: '',
      embeddingError: ''
    });
  },
  onEmbeddingBaseUrlInput(e) { this.setData({ embeddingBaseUrl: e.detail.value }); },
  onEmbeddingModelInput(e) { this.setData({ embeddingModel: e.detail.value }); },

  onOpenSiliconflow() {
    wx.setClipboardData({
      data: 'https://cloud.siliconflow.cn',
      success: () => wx.showToast({ title: '官网已复制', icon: 'success' })
    });
  },

  async onVerifyEmbedding() {
    const { embeddingApiKey, embeddingBaseUrl, embeddingModel } = this.data;
    if (!embeddingApiKey || !embeddingApiKey.startsWith('sk-')) {
      wx.showToast({ title: 'Embedding Key 格式不对', icon: 'none' });
      return;
    }

    this.setData({ embeddingVerifying: true, embeddingMsg: '', embeddingError: '' });

    try {
      const res = await request('/user/config/verify_embedding', 'POST', {
        embedding_api_key: embeddingApiKey,
        embedding_base_url: embeddingBaseUrl,
        embedding_model: embeddingModel
      });
      if (res.success) {
        this.setData({ embeddingVerifying: false, embeddingVerified: true, embeddingMsg: res.message });
      } else {
        this.setData({ embeddingVerifying: false, embeddingVerified: false, embeddingError: res.message });
      }
    } catch (err) {
      this.setData({ embeddingVerifying: false, embeddingVerified: false, embeddingError: '测试失败: ' + err.message });
    }
  },

  // ========== 通用 ==========
  onOpenConsole() {
    const p = PROVIDERS[this.data.providerIndex];
    if (!p.console) {
      wx.showToast({ title: '自定义厂商无官网', icon: 'none' });
      return;
    }
    wx.setClipboardData({
      data: p.console,
      success: () => wx.showToast({ title: '官网已复制', icon: 'success' })
    });
  },

  async onVerify() {
    const { apiKey, baseUrl, llmModel } = this.data;
    if (!apiKey || !apiKey.startsWith('sk-')) {
      wx.showToast({ title: 'API Key 格式不对', icon: 'none' });
      return;
    }

    this.setData({ verifying: true, verifyMsg: '', verifyError: '' });

    try {
      const res = await request('/user/config/verify', 'POST', {
        llm_api_key: apiKey,
        llm_base_url: baseUrl,
        llm_model: llmModel
      });
      if (res.success) {
        this.setData({ verifying: false, verified: true, verifyMsg: res.message });
      } else {
        this.setData({ verifying: false, verified: false, verifyError: res.message });
      }
    } catch (err) {
      this.setData({ verifying: false, verified: false, verifyError: '测试失败: ' + err.message });
    }
  },

  async onSave() {
    const {
      apiKey, baseUrl, llmModel, useSameForVision, visionApiKey, visionBaseUrl, visionModel,
      embeddingApiKey, embeddingBaseUrl, embeddingModel
    } = this.data;

    if (!this.data.verified) {
      wx.showToast({ title: '请先测试文本连接', icon: 'none' });
      return;
    }

    this.setData({ saving: true });

    try {
      await request('/user/config', 'PUT', {
        llm_provider: PROVIDERS[this.data.providerIndex].key,
        llm_api_key: apiKey,
        llm_base_url: baseUrl,
        llm_model: llmModel,
        vision_provider: PROVIDERS[this.data.visionProviderIndex].key,
        vision_api_key: useSameForVision ? '' : visionApiKey,
        vision_base_url: useSameForVision ? '' : visionBaseUrl,
        vision_model: visionModel,
        embedding_api_key: embeddingApiKey,
        embedding_base_url: embeddingBaseUrl,
        embedding_model: embeddingModel
      });

      wx.showToast({ title: '保存成功', icon: 'success' });
      setTimeout(() => {
        wx.navigateBack({
          fail: () => wx.switchTab({ url: '/pages/index/index' })
        });
      }, 800);
    } catch (err) {
      this.setData({ saving: false });
      wx.showModal({ title: '保存失败', content: err.message, showCancel: false });
    }
  }
})