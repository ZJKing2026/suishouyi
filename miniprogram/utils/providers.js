// utils/providers.js
// 常见厂商的预设配置（用于自动填充）
export const PROVIDERS = [
  {
    key: 'deepseek',
    name: 'DeepSeek',
    baseUrl: 'https://api.deepseek.com/v1',
    llmModel: 'deepseek-chat',
    // DeepSeek 暂无视觉模型，需要视觉能力时请改用下方其它厂商
    visionModel: '',
    console: 'https://platform.deepseek.com'
  },
  {
    key: 'openai',
    name: 'OpenAI',
    baseUrl: 'https://api.openai.com/v1',
    llmModel: 'gpt-4o-mini',
    visionModel: 'gpt-4o',
    console: 'https://platform.openai.com'
  },
  {
    key: 'qwen',
    name: '通义千问',
    baseUrl: 'https://dashscope.aliyuncs.com/compatible-mode/v1',
    llmModel: 'qwen-plus',
    visionModel: 'qwen-vl-plus',
    console: 'https://dashscope.console.aliyun.com'
  },
  {
    key: 'moonshot',
    name: '月之暗面 Kimi',
    baseUrl: 'https://api.moonshot.cn/v1',
    llmModel: 'moonshot-v1-8k',
    visionModel: 'moonshot-v1-8k-vision-preview',
    console: 'https://platform.moonshot.cn'
  },
  {
    key: 'zhipu',
    name: '智谱 GLM',
    baseUrl: 'https://open.bigmodel.cn/api/paas/v4',
    llmModel: 'glm-4-flash',
    visionModel: 'glm-4v',
    console: 'https://open.bigmodel.cn'
  },
  {
    key: 'custom',
    name: '自定义',
    baseUrl: '',
    llmModel: '',
    visionModel: '',
    console: ''
  }
];

export function getProvider(key) {
  return PROVIDERS.find(p => p.key === key) || PROVIDERS[0];
}