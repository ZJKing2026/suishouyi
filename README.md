<div align="center">

# 随手一下

**一个会替你办事的 AI——大事会先问你。**

微信小程序 + FastAPI。语音、图片、文件、网页扔进来就出结果；
联系人交给 AI 去交涉，但凡是涉及你本人的事，AI 一定先请示你。

[![License](https://img.shields.io/badge/license-MIT-17161a.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.11+-3776ab.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688.svg)](https://fastapi.tiangolo.com/)
[![WeChat](https://img.shields.io/badge/WeChat-MiniProgram-07c160.svg)](https://developers.weixin.qq.com/miniprogram/dev/framework/)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-e0623c.svg)](CONTRIBUTING.md)
[![Stars](https://img.shields.io/github/stars/ZJKing2026/suishouyi?style=social)](https://github.com/ZJKing2026/suishouyi/stargazers)

[这是什么](#这是什么) · [AI 代理](#ai-代理最核心的部分) · [快速开始](#快速开始) · [架构](#架构) · [参与贡献](#参与贡献)

</div>

---

## 这是什么

「随手一下」解决两个很具体的问题。

**第一个：我不想为了处理一个东西，先去研究该用哪个工具。**

- 拍一张菜单照片 → 直接问「这上面哪个不辣」
- 录一段会议录音 → 直接拿到逐字稿和要点
- 丢一个 PDF 合同 → 直接问「违约金怎么算」

没有「请选择功能」这一步。一个输入框，剩下的交给意图路由。

**第二个：我不想为了约个时间，来回聊十轮。**

- 你想问朋友一件事 → 告诉 AI，它去问，对方 AI 答完回来告诉你
- 对方拿不准 → 对方 AI 会先请示他本人，不会替他瞎答应
- 你收到一份要决策的请示 → 点「按建议回复」，剩下的 AI 自己走完

区别在于：**AI 不装成你，它是你的代理。** 市面上多数「AI 社交」是让模型扮演你去聊天，
这里不是——AI 明确知道自己是助理，明确知道自己不知道你的日程，所以它会问。

### 和同类项目的区别

| | 随手一下 | 典型的 AI 聊天壳 |
|---|---|---|
| 交互入口 | 单一输入框，自动判断意图 | 一堆功能按钮，用户自己选 |
| 代理行为 | 遇到涉及主人的事**必须请示** | 模型自由发挥，编造你的日程 |
| 模型接入 | **用户自带 API Key** | 平台代付，作者每月烧钱 |
| 能力扩展 | 工具市场 + MCP 协议 + OpenAPI 导入 | 硬编码在代码里 |
| 部署成本 | 一个 SQLite 文件，零外部依赖 | 要 Redis / PostgreSQL / 向量库 |

**关于「用户自带 Key」**：这是刻意的设计选择。作者不承担推理成本，所以这个项目可以一直
免费开源下去，不会因为账单而跑路。代价是你需要自己去
[DeepSeek 开放平台](https://platform.deepseek.com/) 申请一个 Key（注册送额度，个人用基本够）。

---

## AI 代理（最核心的部分）

这是这个项目和普通聊天机器人拉开差距的地方。

### 一次代理咨询的完整流程

```
你：「帮我问问张三明天有空吗」
 │
 └─ 你的 AI 去问张三的 AI
     │
     ├─ 【对方 AI 能自己答】寒暄、公开信息 → 直接回复你，你什么都不用做
     │
     └─ 【涉及张三本人】时间 / 日程 / 隐私 / 承诺 / 动用资源
         │
         ├─ 张三的 AI **不猜**，而是给张三弹一条请示：
         │     ┌──────────────────────────────┐
         │     │ 🤖 AI 需要你决策              │
         │     │ 李四问：明天有空吗？           │
         │     │ AI 查到的依据：……             │
         │     │ AI 建议：回复「下午可以」       │
         │     │ [按建议回复] [自定义] [拒绝]    │
         │     └──────────────────────────────┘
         │
         └─ 张三拍板 → AI 才把答复发回给李四
```

### 权限边界是怎么定的

**AI 可以自己决定的：** 打招呼、寒暄、事实性问题、礼貌拒绝推销、无风险的社交回应。

**AI 必须请示主人的：**

| 类别 | 例子 |
|---|---|
| 时间 | 「明天有空吗」「周末要不要一起」 |
| 隐私 | 行程、资料、联系方式、住址 |
| 承诺 | 「能帮我出份文档吗」 |
| 资源 | 发文件、发资料、动用账号 |
| 拿不准 | 任何模型自己没把握判断的 |

实现上是**两道闸**：先用规则预筛（命中上面任何一类直接升级，不给模型机会），
规则放行后才让模型判定，且**模型输出解析失败时一律按"要请示"处理**。
宁可多问一句，绝不替用户瞎答应。

### 为什么 AI 不装成你

早期版本让 AI「用第一人称扮演本人」。这个做法有个致命问题：
模型没有你的日历、没有你的通讯录，被问到「明天有空吗」时它**会编**。

现在改成了：AI 明确以助理身份出现，不知道的事就说「我需要先跟本人确认一下」。
看似少了点「拟人感」，但换来了一个可信的代理——它不会替你答应你没答应过的事。

---

## 功能

### 输入侧——什么都收

| 能力 | 说明 |
|---|---|
| 💬 **对话** | 多轮上下文，支持 Markdown 渲染 |
| 🎙 **语音** | 录音 → Whisper 本地转录 → 自动填入输入框 |
| 📷 **图片** | 拍照/相册 → 视觉模型理解 → OCR 提取文字 |
| 📄 **文件** | PDF / Word / Markdown / TXT 解析 → 摘要 → 入库 |
| 🌐 **网页** | 粘贴 URL → 抓正文 → 摘要 |

### 社交侧

- **好友**：邀请码加好友、单聊、未读汇总
- **AI 代问**：让 AI 替你去问好友，对方拿不准会先请示本人
- **群聊**：建群、群主拉人、AI 代发消息
- **群 AI 讨论**：群里所有人的 AI 轮流发言，聊完自动出总结（后台跑，前端轮询进度）

### 处理侧——意图路由

后端有一套规则意图分类器（`app/ai/router/intent.py`），根据输入内容和上下文判断用户想做什么，
自动选择合适的处理链路。不依赖额外的模型调用，零延迟零成本。

### 扩展侧——三条路

1. **技能市场** —— 预置工具一键启用：天气、计算、时间、网页摘要、邮件发送
2. **自定义工具** —— 填一个 HTTP 接口，用 `{param}` 占位符定义参数，AI 就能调用
3. **MCP 协议** —— 接入任意 MCP Server，工具自动注册进 AI 的工具列表

还支持 **OpenAPI 导入**：贴一个 Swagger 文档地址，自动解析成可用工具。

### 知识库

上传 PDF/Markdown → 切分（500 字/50 重叠）→ Embedding → 存储。
对话时可开关 RAG，开启后先检索再回答。

### 其他

- **笔记**：录音转写 + AI 摘要 + 关键点提取，详情可导出成图片
- **求职助手**：简历优化、JD 匹配度分析、求职信生成
- **工具箱**：8 个即用型文件处理工具，无需 AI Key

---

## 快速开始

### 前置要求

- Python 3.11+
- [微信开发者工具](https://developers.weixin.qq.com/miniprogram/dev/devtools/download.html)
- 一个 DeepSeek API Key（[点此申请](https://platform.deepseek.com/)）

### 1. 启动后端

```bash
git clone https://github.com/ZJKing2026/suishouyi.git
cd suishouyi/backend

python -m venv .venv

# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

pip install -r requirements.txt

cp .env.example .env
```

编辑 `.env`，至少填上这一项：

```env
LLM_API_KEY=sk-你的key
```

启动：

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

打开 http://localhost:8000/docs 可以看到完整的 API 文档。
看到 `✅ 预置工具已就绪` 就说明初始化成功了。

> **首次启动会慢**：如果启用了语音转录，`faster-whisper` 需要下载模型文件（约 150MB）。只在第一次。

### 2. 启动小程序

用微信开发者工具打开 `miniprogram/` 目录。

**改后端地址**——编辑 `miniprogram/utils/config.js`：

```js
// 本机调试用这个
export const BASE_URL = 'http://localhost:8000/api/v1';

// 真机预览需要局域网 IP，或者用内网穿透
```

> ⚠️ 微信开发者工具需要勾选「不校验合法域名」才能连 localhost。真机调试必须用 HTTPS 域名。

### 3. 配置 API Key

小程序里进入「设置」页，填入你的 DeepSeek Key。

Key 存在哪？——**存在你自己的后端数据库里**，绑定在你的微信账号上。
项目不会把它发给任何第三方，只会用来调用你自己配置的模型接口。

#### 可选：配置视觉模型

默认配置里视觉模型是关闭的（`VISION_MOCK`）。如果要处理图片，需要一个支持视觉的
OpenAI 兼容接口。DeepSeek 目前没有视觉模型，可以换成别的服务商——在 `.env` 里独立配置：

```env
VISION_MOCK=false
VISION_API_KEY=sk-xxx
VISION_BASE_URL=https://api.openai.com/v1
VISION_MODEL=gpt-4o-mini
```

#### 可选：配置 Embedding

知识库需要 Embedding 模型。这个同样是在小程序「设置」页里配置，不在 `.env`。

没配置的话，用到知识库功能时会提示你去配置。

---

## 架构

```
suishouyi/
├── backend/                     FastAPI 服务
│   ├── app/
│   │   ├── api/v1/              路由模块
│   │   ├── ai/
│   │   │   ├── agent/           Agent 循环 + 工具执行器
│   │   │   ├── llm/             LLM 客户端与工厂
│   │   │   ├── vision/          视觉模型客户端
│   │   │   └── router/          意图分类路由
│   │   ├── core/                配置、安全、日志
│   │   ├── models/              SQLAlchemy 模型
│   │   ├── schemas/             Pydantic 模型
│   │   └── services/            业务服务
│   ├── tests/                   状态机端到端验证
│   └── requirements.txt
│
└── miniprogram/                 微信小程序
    ├── app.wxss                 全局设计系统（颜色/字号/间距变量）
    ├── pages/                   页面
    └── utils/                   请求、认证、上传、Markdown、UI 工具
```

### 请求是怎么走的

```
用户输入
   │
   ├─ 纯文本 ──→ 意图路由 ──→ Agent 循环 ──→ LLM
   │                              │
   │                              └─→ 工具调用（内置 / 自定义 / MCP）
   │
   ├─ 语音 ────→ Whisper 转录 ──┐
   ├─ 图片 ────→ 视觉模型 ──────┤
   ├─ 文件 ────→ 解析器 ────────┼─→ 文本 ──→ 同上
   └─ 网页 ────→ 正文提取 ──────┘
```

### AI 代理任务是怎么跑的

```
agent_tasks 状态机
   │
   ├─ running         正在执行
   ├─ waiting_user    卡在请示，等主人拍板
   ├─ waiting_peer    卡在等对方 AI
   ├─ done / failed
   │
   └─ 超时（10 分钟无决策）自动收尾
```

**关键设计：任何"等人"的环节都落库挂起，内存里不留悬挂协程。**

所以不需要 Celery、不需要 Redis、不需要定时器，进程重启也不丢任务。
超时是"延迟触发"的——下次有人读请示时才顺手清理，省掉一个后台调度器。
代价是每一步都要显式写出"下一步该干嘛"，实现上比 `await` 啰嗦，
但换来的是和「一个 SQLite 文件」这个定位不冲突。

### 技术选型说明

**为什么用 SQLite？** 个人助手的数据量不需要 PostgreSQL。SQLite 让「克隆下来就能跑」成为可能——
不需要装数据库、不需要配 docker-compose。上面那套状态机方案也是为它让路的。

**为什么 RAG 用内存余弦检索？** 个人知识库通常几百到几千个 chunk，numpy 级别的计算完全够用。
引入向量数据库会让部署复杂度上升一个量级，不值得。

**为什么意图路由用规则而不是模型？** 每次对话前先调一次模型做意图分类，既慢又费钱。
规则分类器在这个场景下准确率足够，且零成本。

**为什么请示要用规则预筛而不是全交给模型？** 涉及隐私的事，模型判断失误的代价不对称——
多问一句只是麻烦，替用户答应了不该答应的事是事故。

---

## 参与贡献

这个项目**很需要你**。我不可能一个人把所有方向都做完。

### 最容易上手的方向

不需要懂整个项目，挑一个就行：

| 方向 | 具体任务 | 难度 |
|---|---|---|
| 📝 文档 | 补一段部署教程、翻译 README 到英文 | ⭐ |
| 🐛 Bug | 翻 [Issues](https://github.com/ZJKing2026/suishouyi/issues) 找 `good first issue` | ⭐⭐ |
| 🎨 UI | 挑一个页面重新设计（设计变量都在 `app.wxss`） | ⭐⭐ |
| 🔌 工具 | 往技能市场里加新工具 | ⭐⭐ |
| 🧪 测试 | 后端测试覆盖还很少，多写一个就是突破 | ⭐⭐ |
| 🤖 模型 | 接入除 DeepSeek 外的模型服务商 | ⭐⭐⭐ |
| 🧠 代理 | 让 AI 代理支持多轮协商、代办任务 | ⭐⭐⭐⭐ |
| 🔍 检索 | 把 RAG 换成真正的向量索引（sqlite-vec / pgvector） | ⭐⭐⭐⭐ |

### 提交前请先看

- [CONTRIBUTING.md](CONTRIBUTING.md) —— 开发环境、代码规范、PR 流程
- [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md) —— 社区约定

### 提 Issue 的时候

请带上：**复现步骤**、**期望行为**、**实际行为**、**错误日志**。只有一个「不工作」的 Issue 很难排查。

---

## 路线图

### 已完成

- [x] 多轮对话 + 意图路由
- [x] 语音转录 / 图片理解 / 文件解析 / 网页摘要
- [x] RAG 知识库
- [x] 技能市场 + 自定义工具 + MCP 协议 + OpenAPI 导入
- [x] 笔记（含图片导出）、求职助手、全局设计系统
- [x] 好友系统（邀请码、单聊、未读汇总）
- [x] 群聊（建群、拉人、AI 代发、AI 自主讨论）
- [x] **AI 代理请示机制**——涉及主人的事必须请示，不再由模型臆测
- [x] 代理任务状态机（重启不丢任务，零外部依赖）

### 进行中

- [ ] AI 双向多轮协商（目前是单轮问答 + 请示）
- [ ] 群聊 @AI 触发讨论（现在要手动点按钮）
- [ ] 补齐后端单元测试
- [ ] OCR 模块实现（目前图片走视觉模型，独立 OCR 待补）

### 计划

- [ ] AI 代办任务：查知识库 → 生成文档 → 发给对方
- [ ] 向量索引替换内存检索
- [ ] 更多模型服务商适配
- [ ] 会话导出 / 分享
- [ ] 深色模式
- [ ] 英文文档

有想法？开个 [Issue](https://github.com/ZJKing2026/suishouyi/issues) 聊。

---

## 常见问题

<details>
<summary><b>为什么一定要自己的 API Key？</b></summary>

因为作者付不起所有人的推理账单。自带 Key 让项目能长期免费开源，而不是烧完钱就归档。

申请 DeepSeek Key 有免费额度，个人日常使用完全够。
</details>

<details>
<summary><b>AI 会不会替我乱答应事情？</b></summary>

这是设计上最在意的一点，做了三层防护：

1. **规则预筛**：涉及时间、隐私、承诺、资源的问题，直接升级给你，不给模型判断的机会
2. **模型判定**：剩下的交给模型，但输出解析失败时一律按"要请示"处理
3. **拒绝臆测**：AI 不持有你的日历和通讯录，提示词明确要求不知道就说"需要确认"

换句话说，它宁可多问你一句，也不会替你做主。
</details>

<details>
<summary><b>能换成其他模型吗？</b></summary>

可以。任何 OpenAI 兼容接口都行——改 `.env` 里的 `LLM_BASE_URL` 和 `LLM_MODEL` 即可。
视觉模型是独立配置的，可以和服务商不一样。
</details>

<details>
<summary><b>我的 API Key 安全吗？</b></summary>

Key 存在你自己部署的后端数据库里，绑定在你的微信账号下。

需要提醒的是：**这是明文存储**。如果你部署在公网，请确保数据库文件不被他人访问。
相关改进见 Issue 区。
</details>

<details>
<summary><b>第一次启动卡住了？</b></summary>

大概率是 Whisper 在下载模型。等一两分钟，或者先把语音相关依赖去掉。
</details>

<details>
<summary><b>小程序连不上后端？</b></summary>

三个检查点：
1. 开发者工具里勾选「不校验合法域名」
2. `utils/config.js` 的 `BASE_URL` 指向正确
3. 真机调试必须用 HTTPS，不能用 localhost
</details>

---

## 致谢

感谢所有贡献者。你们的每一次提交（哪怕是改一个错别字）都让这个项目更好。

<a href="https://github.com/ZJKing2026/suishouyi/graphs/contributors">
  <img src="https://contrib.rocks/image?repo=ZJKing2026/suishouyi" />
</a>

## 许可证

[MIT](LICENSE) —— 随便用，商用也行，改了不用告诉我。留个 Star 就好。

---

<div align="center">

**如果这个项目帮你省下了一点时间，点个 ⭐ 吧。**

那是我继续做下去的主要动力。

</div>
