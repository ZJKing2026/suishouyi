// pages/about/about.js
import { GITHUB_URL, APP_VERSION } from '../../utils/config.js';

Page({
  data: {
    version: APP_VERSION,
    githubUrl: GITHUB_URL,

    features: [
      { icon: '💬', name: 'AI 对话', desc: '多轮对话 + 自动调用工具' },
      { icon: '📚', name: '知识库问答', desc: '上传文档，AI 基于它回答（RAG）' },
      { icon: '🎙', name: '语音笔记', desc: '录音转文字 + AI 摘要' },
      { icon: '💼', name: '求职助手', desc: '简历优化 / JD 匹配 / 求职信' },
      { icon: '🧰', name: '工具箱', desc: '图片压缩 / 二维码 / PDF / 加水印' },
      { icon: '🤖', name: 'Agent 任务链', desc: 'AI 自主规划多步、串联工具' },
      { icon: '🔌', name: 'MCP 协议', desc: '接入 Anthropic 生态的 MCP 服务器' },
      { icon: '🎯', name: '自定义工具', desc: '接入任意 HTTP API 和 OpenAPI 文档' },
    ],

    techStack: [
      { name: '微信小程序', desc: '原生 + TypeScript' },
      { name: 'FastAPI', desc: 'Python 异步 Web 框架' },
      { name: 'SQLAlchemy', desc: 'ORM 数据库层' },
      { name: 'OpenAI 兼容接口', desc: 'DeepSeek / OpenAI / Qwen 可切换' },
      { name: 'SiliconFlow Embedding', desc: 'BGE-M3 向量化（知识库）' },
      { name: 'faster-whisper', desc: '本地语音转文字' },
      { name: 'SQLite', desc: '开发数据库 + RAG 向量存储' },
    ]
  },

  onCopyGithub() {
    wx.setClipboardData({
      data: GITHUB_URL,
      success: () => {
        wx.showToast({
          title: '链接已复制',
          icon: 'success'
        });
      }
    });
  },

  onOpenGithub() {
    wx.setClipboardData({
      data: GITHUB_URL,
      success: () => {
        wx.showModal({
          title: '已复制链接',
          content: '链接已复制到剪贴板，请在浏览器中打开',
          showCancel: false,
          confirmText: '知道了'
        });
      }
    });
  }
})