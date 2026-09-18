// pages/process/process.js
import { request } from '../../utils/request.js';

Page({
  data: {
    inputText: '',    // 用户输入
    loading: false,   // 是否处理中
    result: '',       // AI 结果
    taskType: ''      // 任务类型
  },

  // 输入框内容变化
  onInput(e) {
    this.setData({ inputText: e.detail.value });
  },

  // 点击「丢给AI」
  async onSubmit() {
    const text = this.data.inputText.trim();
    if (!text) return;

    this.setData({ loading: true, result: '', taskType: '' });

    try {
      // 调用后端接口
      const res = await request('/tasks', 'POST', { content: text });

      // 显示结果
      this.setData({
        loading: false,
        result: res.output_text,
        taskType: res.task_type
      });
    } catch (err) {
      this.setData({ loading: false, result: '请求失败：' + err.message });
    }
  }
})