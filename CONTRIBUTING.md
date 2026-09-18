# 贡献指南

先说一句：**欢迎任何人以任何形式参与**。改错别字、提 Issue、翻译文档，都算。

不用怕「我的代码不够好」。这是个个人项目，没有代码洁癖，能跑通、能读懂就够。

---

## 目录

- [我想帮忙但不知道做什么](#我想帮忙但不知道做什么)
- [搭建开发环境](#搭建开发环境)
- [代码规范](#代码规范)
- [提交 Pull Request](#提交-pull-request)
- [报告 Bug](#报告-bug)
- [提功能建议](#提功能建议)

---

## 我想帮忙但不知道做什么

去 [Issues](https://github.com/ZJKing2026/suishouyi/issues) 看标签：

| 标签 | 含义 |
|---|---|
| `good first issue` | 特意留的入门任务，通常改动很小 |
| `help wanted` | 明确需要外部帮助 |
| `enhancement` | 功能改进 |
| `bug` | 待修复的问题 |
| `documentation` | 文档相关 |

**特别缺人的方向**（按急需程度排）：

1. **后端测试** —— 目前测试覆盖是 **零**。写第一个测试的人会名留青史。
2. **UI 改进** —— 设计系统（`miniprogram/app.wxss`）已经搭好，改页面很快。
3. **英文文档** —— 让项目能被更多人看到。

如果你想做但不确定从哪下手，直接开个 Issue 问，我会指路。

---

## 搭建开发环境

### 后端

```bash
cd backend

python -m venv .venv

# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

pip install -r requirements.txt

cp .env.example .env
# 编辑 .env，填入你的 LLM_API_KEY

uvicorn app.main:app --reload --port 8000
```

访问 http://localhost:8000/docs 看 API 文档。

### 小程序

微信开发者工具打开 `miniprogram/` 目录，改 `utils/config.js` 里的 `BASE_URL` 指向你的后端。

在开发者工具里勾选 **详情 → 本地设置 → 不校验合法域名**。

### 不想花 API 钱？

把 `.env` 里的 `AI_MOCK` 设为 `true`，AI 相关接口会返回模拟数据。开发 UI 或跑测试时用这个。

---

## 代码规范

### Python

- 遵循 PEP 8
- 所有函数必须有**中文 docstring**，说明功能、参数、返回值
- 关键逻辑加中文行内注释，解释**为什么**这么做，而不是复述代码在做什么
- 变量命名用英文，见名知意
- 不要写「根据需求」「按用户要求」这类无信息量的注释

```python
def split_document(text: str, chunk_size: int = 500, overlap: int = 50) -> list[str]:
    """把长文本按固定长度切分成有重叠的片段。

    Args:
        text: 待切分的原始文本
        chunk_size: 每段的字符数上限
        overlap: 相邻片段的重叠字符数，避免语义在边界处被切断

    Returns:
        切分后的文本片段列表
    """
    # 重叠区域保证跨段的句子不会丢失上下文
    ...
```

### 小程序

- WXSS 里**禁止**写死颜色和圆角，一律用 `app.wxss` 里的 CSS 变量
- 新页面根节点用 `.page` 类，不要再定义 padding
- 可点击元素加 `.tappable` 类统一手感
- JS 里不要留 `console.log`，错误用 `console.error` 并给用户反馈

可用的设计变量：

```css
/* 颜色 */
var(--ink) var(--ink-soft) var(--ink-muted) var(--ink-faint) var(--ink-ghost)
var(--bg) var(--bg-sunken) var(--surface) var(--line) var(--line-soft)
var(--accent) var(--accent-soft) var(--accent-deep)
var(--ok) var(--warn) var(--danger) var(--info)

/* 字号 */
var(--fs-hero) var(--fs-title) var(--fs-subtitle)
var(--fs-body) var(--fs-small) var(--fs-tiny)

/* 间距 / 圆角 */
var(--sp-page) var(--sp-lg) var(--sp-md) var(--sp-sm) var(--sp-xs)
var(--r-card) var(--r-btn) var(--r-chip) var(--r-sm)
```

### 通用

- 提交信息用中文或英文都行，说清楚**为什么改**
- 一次 PR 只做一件事，不要把重构和新功能混在一起
- **绝对不要**把 API Key、token、密码写进代码或提交到仓库

---

## 提交 Pull Request

1. Fork 仓库
2. 建分支：`git checkout -b feat/你的功能名`
3. 改代码
4. 自查一遍（见下方清单）
5. 提交：`git commit -m "feat: 添加了什么功能"`
6. 推送：`git push origin feat/你的功能名`
7. 在 GitHub 上开 PR，说明你改了什么、为什么改

### 提交前自查

- [ ] 后端能启动：`uvicorn app.main:app --reload` 无报错
- [ ] 小程序能编译：微信开发者工具无报错
- [ ] 改动涉及 UI 的话，在模拟器里看过实际效果
- [ ] 没有引入新的硬编码密钥
- [ ] 没有提交 `.env`、`.db`、`uploads/` 里的文件

### 提交信息格式

```
feat: 新增功能
fix: 修复问题
docs: 文档变更
style: 格式调整（不影响逻辑）
refactor: 重构（不改变行为）
test: 测试相关
chore: 构建/依赖调整
```

---

## 报告 Bug

好的 Bug 报告能省下大量来回沟通。请包含：

**必填：**
- 复现步骤（越具体越好）
- 期望行为 vs 实际行为
- 错误日志 / 截图

**加分：**
- 你的环境（操作系统、Python 版本、小程序基础库版本）
- 是否稳定复现
- 你自己排查到哪一步

**不要提交：**
- 只写「不工作」「报错了」—— 这类 Issue 很难处理
- 包含你的 API Key 的日志截图

---

## 提功能建议

先说清楚**你要解决什么问题**，而不是直接说「加个 XX 功能」。

- ❌「加一个导出功能」—— 不知道要导出什么、给谁用
- ✅「我经常需要把对话记录发给同事，现在只能截图，很不方便」—— 问题清晰，实现方式可以讨论

如果功能超出项目定位（比如「做成完整的团队协作平台」），我会说明并婉拒。这是一个**个人助手**，不是企业工具。

---

## 最后

有任何问题，直接在 Issue 里问。不会因为问题「太简单」而被嘲笑。

这个项目存在的意义之一，就是让更多人能上手 AI 应用开发。
