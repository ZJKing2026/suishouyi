"""内置工具定义：基础 + 知识库 + 笔记 + 好友。"""
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


# ==================== 知识库工具 ====================

async def search_knowledge_base(db, user_id: int, query: str) -> str:
    try:
        from app.services.rag_service import rag_service, MissingEmbeddingConfigError
        try:
            retrieved = await rag_service._retrieve(db, user_id, query, top_k=5)
        except MissingEmbeddingConfigError:
            return "错误：用户还没配置知识库（Embedding Key）"

        if not retrieved:
            return "知识库里没有找到相关内容"

        lines = []
        for i, r in enumerate(retrieved):
            snippet = r["content"][:500]
            lines.append(f"[片段 {i+1}] 相似度 {r['similarity']}\n{snippet}")
        return "\n\n---\n\n".join(lines)
    except Exception as e:
        return f"检索失败：{str(e)}"


# ==================== 笔记工具 ====================

async def save_note(db, user_id: int, title: str, content: str) -> str:
    try:
        from app.models.note import Note
        note = Note(
            user_id=user_id, title=title[:100] or "AI 生成的笔记",
            transcript=content, summary=content[:200],
            key_points="", status="done", audio_duration=0,
        )
        db.add(note)
        db.commit()
        db.refresh(note)
        return f"已保存到笔记，ID={note.id}，标题：{note.title}"
    except Exception as e:
        return f"保存失败：{str(e)}"


# ==================== 好友工具 ====================

async def list_friends(db, user_id: int) -> str:
    try:
        from app.services.friend_service import friend_service
        friends = friend_service.list_friends(db, user_id)
        if not friends:
            return "你还没有好友。可以邀请微信好友加入，通过好友列表管理。"
        lines = [f"共有 {len(friends)} 位好友："]
        for f in friends:
            lines.append(f"- {f['nickname']}（ID: {f['friend_id']}）")
        return "\n".join(lines)
    except Exception as e:
        return f"获取好友失败：{str(e)}"


async def send_to_friend(db, user_id: int, friend_name: str, message: str) -> str:
    """单方面发消息给好友（不等待回复）。"""
    try:
        from app.services.friend_service import friend_service
        friend = friend_service.find_friend_by_name(db, user_id, friend_name)
        if not friend:
            return f"没有找到名叫「{friend_name}」的好友。可以先让用户用 list_friends 查看。"
        friend_service.send_message(
            db=db, from_user_id=user_id, to_user_id=friend["friend_id"],
            content=message, from_ai=True,
        )
        return f"已给「{friend['nickname']}」发送消息：{message}"
    except Exception as e:
        return f"发送失败：{str(e)}"


async def ask_friend(db, user_id: int, friend_name: str, question: str) -> str:
    """⭐ AI 代理核心工具：问好友并等待好友 AI 自动回答。"""
    try:
        from app.services.friend_service import friend_service
        result = await friend_service.ask_friend_via_ai(
            db, user_id, friend_name, question,
        )
        if not result["success"]:
            return result["message"]
        return f"「{result['friend_name']}」的回答：{result['answer']}"
    except Exception as e:
        return f"问好友失败：{str(e)}"


async def check_messages(db, user_id: int) -> str:
    try:
        from app.services.friend_service import friend_service
        summary = friend_service.get_unread_summary(db, user_id)
        if summary["total_unread"] == 0:
            return "目前没有未读消息。"
        lines = [f"你有 {summary['total_unread']} 条未读消息："]
        for s in summary["summaries"]:
            lines.append(f"- 来自「{s['nickname']}」共 {s['unread_count']} 条，最新：{s['last_content']}")
        return "\n".join(lines)
    except Exception as e:
        return f"查询失败：{str(e)}"


# ==================== 工具 schema ====================

BUILTIN_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "get_current_time",
            "description": "获取当前的日期和时间。",
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
                "properties": {"city": {"type": "string"}},
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
                "properties": {"expression": {"type": "string"}},
                "required": ["expression"]
            }
        }
    },
]

KNOWLEDGE_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "search_knowledge_base",
            "description": "从用户的知识库（上传的文档）中检索相关片段。当用户提到'我上传的'、'我的简历'、'我的文档'时调用。",
            "parameters": {
                "type": "object",
                "properties": {"query": {"type": "string"}},
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
            "description": "把内容保存为一条笔记。当用户说'保存下来'、'存到笔记'时调用。",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "content": {"type": "string"}
                },
                "required": ["title", "content"]
            }
        }
    },
]

FRIEND_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "list_friends",
            "description": "列出当前用户的所有好友。当用户说'给xx发消息'、'联系xx'时，先调用这个。",
            "parameters": {"type": "object", "properties": {}, "required": []}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "ask_friend",
            "description": "⭐ 让 AI 代表用户去问好友一个问题，好友的 AI 会自动回答。当用户说'帮我问问xx'、'帮我问xx'、'xx怎么看'、'xx怎么说'时调用。这是 AI 代理的核心能力。",
            "parameters": {
                "type": "object",
                "properties": {
                    "friend_name": {"type": "string", "description": "好友昵称"},
                    "question": {"type": "string", "description": "要问的问题"}
                },
                "required": ["friend_name", "question"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "send_to_friend",
            "description": "单方面给好友发消息（不等待回复）。当用户说'告诉xx'、'通知xx'时调用。",
            "parameters": {
                "type": "object",
                "properties": {
                    "friend_name": {"type": "string"},
                    "message": {"type": "string"}
                },
                "required": ["friend_name", "message"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "check_messages",
            "description": "查看未读消息。",
            "parameters": {"type": "object", "properties": {}, "required": []}
        }
    },
]


# ==================== 工具函数注册表 ====================

BUILTIN_FUNCTIONS = {
    "get_current_time": get_current_time,
    "get_weather": get_weather,
    "calculate": calculate,
}

CONTEXT_FUNCTIONS = {
    "search_knowledge_base": search_knowledge_base,
    "save_note": save_note,
}

FRIEND_FUNCTIONS = {
    "list_friends": list_friends,
    "ask_friend": ask_friend,
    "send_to_friend": send_to_friend,
    "check_messages": check_messages,
}