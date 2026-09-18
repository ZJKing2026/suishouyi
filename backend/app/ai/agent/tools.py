"""内置工具定义。"""
import json
from datetime import datetime
import re


# ==================== 基础工具 ====================

def get_current_time() -> str:
    now = datetime.now()
    weekday = "一二三四五六日"[now.weekday()]
    return now.strftime(f"%Y-%m-%d %H:%M:%S 星期{weekday}")


def get_weather(city: str) -> str:
    mock_data = {
        "北京": "晴，气温 22-28℃，东南风 2 级",
        "上海": "多云，气温 24-29℃，东风 3 级",
        "广州": "小雨，气温 26-31℃，南风 2 级",
        "深圳": "阴，气温 27-32℃，无持续风向",
        "杭州": "晴转多云，气温 21-27℃，微风",
    }
    return mock_data.get(city, f"{city}今天天气晴朗，气温 20-26℃，微风")


def calculate(expression: str) -> str:
    if not re.fullmatch(r'[\d+\-*/%().\s]+', expression):
        return "错误：表达式包含不允许的字符"
    try:
        result = eval(expression, {"__builtins__": {}}, {})
        return f"计算结果：{expression} = {result}"
    except Exception as e:
        return f"计算错误：{str(e)}"


# ==================== 能力工具（需上下文） ====================

async def search_knowledge_base(db, user_id: int, query: str) -> str:
    """从用户的知识库中检索相关片段。"""
    try:
        from app.services.rag_service import rag_service, MissingEmbeddingConfigError

        try:
            retrieved = await rag_service._retrieve(db, user_id, query, top_k=5)
        except MissingEmbeddingConfigError:
            return "错误：用户还没配置知识库（Embedding Key）"

        if not retrieved:
            return "知识库里没有找到相关内容（可能文档为空或没上传）"

        lines = []
        for i, r in enumerate(retrieved):
            snippet = r["content"][:500]
            lines.append(f"[片段 {i+1}] 相似度 {r['similarity']}\n{snippet}")

        return "\n\n---\n\n".join(lines)
    except Exception as e:
        return f"检索失败：{str(e)}"


async def save_note(db, user_id: int, title: str, content: str) -> str:
    """保存内容到用户的笔记。"""
    try:
        from app.models.note import Note
        from datetime import datetime

        note = Note(
            user_id=user_id,
            title=title[:100] or "AI 生成的笔记",
            transcript=content,
            summary=content[:200],
            key_points="",
            status="done",
            audio_duration=0,
        )
        db.add(note)
        db.commit()
        db.refresh(note)
        return f"已保存到笔记，ID={note.id}，标题：{note.title}"
    except Exception as e:
        return f"保存失败：{str(e)}"


# ==================== 工具 schema ====================

BUILTIN_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "get_current_time",
            "description": "获取当前的日期和时间。当用户问'现在几点'、'今天几号'、'星期几'时调用。",
            "parameters": {"type": "object", "properties": {}, "required": []}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "查询指定城市的实时天气。",
            "parameters": {
                "type": "object",
                "properties": {"city": {"type": "string", "description": "城市名称，如'北京'"}},
                "required": ["city"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "calculate",
            "description": "计算数学表达式。",
            "parameters": {
                "type": "object",
                "properties": {"expression": {"type": "string", "description": "数学表达式，如 '23 * 45 + 12'"}},
                "required": ["expression"]
            }
        }
    },
]

# 知识库工具（只在用户配了 Embedding Key 时提供）
KNOWLEDGE_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "search_knowledge_base",
            "description": "从用户的知识库（上传的文档）中检索相关片段。当用户提到'我上传的'、'我的简历'、'我的文档'、'根据资料'时调用。",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "检索关键词或问题"}
                },
                "required": ["query"]
            }
        }
    },
]

NOTE_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "save_note",
            "description": "把内容保存为一条笔记。当用户说'保存下来'、'存到笔记'、'记录一下'，或你生成了值得保存的长内容（如求职信、方案）时调用。",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "笔记标题（15字内）"},
                    "content": {"type": "string", "description": "笔记正文"}
                },
                "required": ["title", "content"]
            }
        }
    },
]


# ==================== 工具函数注册表 ====================

BUILTIN_FUNCTIONS = {
    "get_current_time": get_current_time,
    "get_weather": get_weather,
    "calculate": calculate,
}

# 需要上下文的工具（异步 + db + user_id）
CONTEXT_FUNCTIONS = {
    "search_knowledge_base": search_knowledge_base,
    "save_note": save_note,
}