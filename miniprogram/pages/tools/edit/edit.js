// pages/tools/edit/edit.js
import { request } from '../../../utils/request.js';

const METHODS = ['GET', 'POST'];

Page({
  data: {
    toolId: null,
    isEdit: false,

    name: '',
    description: '',
    parametersSchema: '{"type":"object","properties":{},"required":[]}',
    apiUrl: '',
    apiMethod: 'GET',
    headers: '{}',
    enabled: true,

    // 测试
    testArguments: '{}',
    testResult: '',
    testSuccess: false,
    testing: false,

    saving: false,

    methods: METHODS,
    methodIndex: 0
  },

  onLoad(options) {
    if (options.id) {
      this.setData({ toolId: parseInt(options.id), isEdit: true });
      wx.setNavigationBarTitle({ title: '编辑工具' });
      this.loadTool(options.id);
    } else {
      wx.setNavigationBarTitle({ title: '创建工具' });
    }
  },

  async loadTool(id) {
    try {
      const res = await request('/tools', 'GET');
      const tool = res.tools.find(t => t.id === parseInt(id));
      if (tool) {
        this.setData({
          name: tool.name,
          description: tool.description,
          parametersSchema: tool.parameters_schema,
          apiUrl: tool.api_url,
          apiMethod: tool.api_method,
          headers: tool.headers,
          enabled: tool.enabled,
          methodIndex: METHODS.indexOf(tool.api_method)
        });
      }
    } catch (err) {
      console.error('加载工具失败:', err);
    }
  },

  // ==================== 输入 ====================
  onNameInput(e) { this.setData({ name: e.detail.value }); },
  onDescInput(e) { this.setData({ description: e.detail.value }); },
  onSchemaInput(e) { this.setData({ parametersSchema: e.detail.value }); },
  onUrlInput(e) { this.setData({ apiUrl: e.detail.value }); },
  onHeadersInput(e) { this.setData({ headers: e.detail.value }); },
  onTestArgsInput(e) { this.setData({ testArguments: e.detail.value }); },

  onMethodChange(e) {
    const idx = parseInt(e.detail.value);
    this.setData({ methodIndex: idx, apiMethod: METHODS[idx] });
  },

  onEnabledChange(e) {
    this.setData({ enabled: e.detail.value });
  },

  // ==================== 测试 ====================
  async onTest() {
    if (!this.data.toolId) {
      wx.showToast({ title: '请先保存工具', icon: 'none' });
      return;
    }

    let args;
    try {
      args = JSON.parse(this.data.testArguments || '{}');
    } catch (err) {
      wx.showToast({ title: '测试参数不是合法 JSON', icon: 'none' });
      return;
    }

    this.setData({ testing: true, testResult: '', testSuccess: false });

    try {
      const res = await request(`/tools/${this.data.toolId}/test`, 'POST', { arguments: args });
      this.setData({
        testing: false,
        testResult: res.result,
        testSuccess: res.success
      });
    } catch (err) {
      this.setData({
        testing: false,
        testResult: err.message,
        testSuccess: false
      });
    }
  },

  // ==================== 保存 ====================
  async onSave() {
    const {
      name, description, parametersSchema, apiUrl, apiMethod, headers, enabled,
      isEdit, toolId
    } = this.data;

    // 校验
    if (!name || !name.trim()) {
      wx.showToast({ title: '请填写工具名', icon: 'none' });
      return;
    }
    if (!description || !description.trim()) {
      wx.showToast({ title: '请填写描述', icon: 'none' });
      return;
    }
    if (!apiUrl || !apiUrl.trim()) {
      wx.showToast({ title: '请填写 API 地址', icon: 'none' });
      return;
    }
    if (!/^https?:\/\//.test(apiUrl.trim())) {
      wx.showToast({ title: 'API 地址必须以 http(s):// 开头', icon: 'none' });
      return;
    }
    try { JSON.parse(parametersSchema); } catch (e) {
      wx.showToast({ title: '参数 Schema 不是合法 JSON', icon: 'none' });
      return;
    }
    try { JSON.parse(headers); } catch (e) {
      wx.showToast({ title: 'Headers 不是合法 JSON', icon: 'none' });
      return;
    }

    this.setData({ saving: true });

    const payload = {
      name: name.trim(),
      description: description.trim(),
      parameters_schema: parametersSchema,
      api_url: apiUrl.trim(),
      api_method: apiMethod,
      headers: headers,
      enabled: enabled
    };

    try {
      let res;
      if (isEdit) {
        res = await request(`/tools/${toolId}`, 'PUT', payload);
      } else {
        res = await request('/tools', 'POST', payload);
        // 创建成功后切到编辑模式，方便用户测试
        this.setData({ toolId: res.id, isEdit: true });
      }

      this.setData({ saving: false });
      wx.showToast({ title: '保存成功', icon: 'success' });

      // 1.5 秒后返回列表
      setTimeout(() => {
        wx.navigateBack();
      }, 1200);
    } catch (err) {
      this.setData({ saving: false });
      wx.showModal({
        title: '保存失败',
        content: err.message,
        showCancel: false
      });
    }
  }
})