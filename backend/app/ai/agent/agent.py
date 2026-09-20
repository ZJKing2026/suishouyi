"""Agent 编排：LLM 与工具/知识库/好友/MCP 的循环交互。"""
import json
from sqlalchemy.orm import Session

from app.models.message import Message
from app.models.user_config import UserConfig
from app.ai.llm.factory import get_llm_client_for_user
from app.ai.agent.tools import (
    BUILTIN_SCHEMAS,
    KNOWLEDGE_SCHEMAS,
    NOTE_SCHEMAS,
    FRIEND_SCHEMAS,
)
from app.ai.agent.executor import execute_tool_async
from app.services.tool_service import tool_service


SYSTEM_PROMPT = """你是一个有工具能力的 AI 助手。
你可以调用工具来帮助用户完成任务。

重要行为准则：
1. 如果用户提到"我上传的"、"我的简历"、"我的文档"、"根据资料"，先调用 search_knowledge_base 检索
2. 如果需要保存长内容（如求职信、方案、报告），调用 save_note 保存
3. ⭐ 如果用户说"帮我问问xx"、"帮我问xx"、"xx怎么看"、"帮我问下xx"——这是让 AI 代理去问好友，直接调用 ask_friend，它会自动返回好友的回复
4. 如果用户说"告诉xx"、"通知xx"——这是单方面通知，调用 send_to_friend
5. 需要多步操作时，一步步来，不要着急回复
6. 回答要简洁、直接、有重点
"""

MAX_TOOL_ROUNDS = 8
MAX_HISTORY = 20


class Agent:
    async def run(
        self,
        db: Session,
        user_id: int,
        session_id: str,
        content: str,
        use_rag: bool = False,
    ) -> dict:
        # 1. 保存用户消息
        user_msg = Message(user_id=user_id, session_id=session_id, role="user", content=content)
        db.add(user_msg)
        db.commit()

        # 2. 查历史
        history = (
            db.query(Message)
            .filter(Message.user_id == user_id, Message.session_id == session_id)
            .order_by(Message.created_at.asc())
            .all()
        )
        if len(history) > MAX_HISTORY:
            history = history[-MAX_HISTORY:]

        # 3. 组装工具列表
        tools_for_llm = list(BUILTIN_SCHEMAS)

        # 3.1 知识库 + 笔记工具
        cfg = db.query(UserConfig).filter(UserConfig.user_id == user_id).first()
        if cfg and cfg.embedding_api_key:
            tools_for_llm.extend(KNOWLEDGE_SCHEMAS)
            tools_for_llm.extend(NOTE_SCHEMAS)

        # 3.1.5 好友工具（每个用户都有）
        try:
            tools_for_llm.extend(FRIEND_SCHEMAS)
        except Exception as e:
            print(f"⚠️ 加载好友工具失败：{e}")

        # 3.2 用户自定义工具
        user_tools = tool_service.list_enabled_tools(db, user_id)
        for t in user_tools:
            try:
                params = json.loads(t.parameters_schema or '{"type":"object","properties":{}}')
            except json.JSONDecodeError:
                params = {"type": "object", "properties": {}}
            tools_for_llm.append({
                "type": "function",
                "function": {
                    "name": t.name,
                    "description": t.description,
                    "parameters": params,
                }
            })

        # 3.3 MCP 工具
        try:
            from app.services.mcp_service import mcp_service
            mcp_servers = mcp_service.list_servers(db, user_id)
            for srv in mcp_servers:
                if not srv.enabled:
                    continue
                srv_tools = mcp_service.parse_cached_tools(srv)
                for mt in srv_tools:
                    full_name = f"mcp{srv.id}__{mt['name']}"
                    tools_for_llm.append({
                        "type": "function",
                        "function": {
                            "name": full_name,
                            "description": f"[来自 {srv.name}] {mt.get('description', '')}",
                            "parameters": mt.get("input_schema", {"type": "object", "properties": {}}),
                        }
                    })
        except Exception as e:
            print(f"⚠️ 加载 MCP 工具失败：{e}")

        # 4. 拼消息
        messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        for msg in history:
            messages.append({"role": msg.role, "content": msg.content})

        # 5. 循环调用
        client = get_llm_client_for_user(db, user_id)
        used_tools = []
        final_reply = ""

        for _ in range(MAX_TOOL_ROUNDS):
            response = await client.chat_with_tools(messages, tools_for_llm)

            if response.get("tool_calls"):
                messages.append({
                    "role": "assistant",
                    "content": response.get("content"),
                    "tool_calls": response["tool_calls"],
                })
                for call in response["tool_calls"]:
                    fn_name = call["function"]["name"]
                    fn_args = call["function"]["arguments"]
                    used_tools.append(fn_name)

                    print(f"🔧 调用工具：{fn_name}({fn_args[:100]})")
                    tool_result = await execute_tool_async(db, user_id, fn_name, fn_args)

                    messages.append({
                        "role": "tool",
                        "tool_call_id": call["id"],
                        "content": tool_result,
                    })
                continue

            final_reply = response.get("content") or ""
            break
        else:
            final_reply = "抱歉，任务比较复杂，请换个更简单的说法再试。"

        # 6. 保存回复
        if used_tools:
            tool_tag = f"\n\n[本次调用了工具：{', '.join(used_tools)}]"
            if tool_tag not in final_reply:
                final_reply += tool_tag

        assistant_msg = Message(
            user_id=user_id, session_id=session_id, role="assistant", content=final_reply
        )
        db.add(assistant_msg)
        db.commit()
        db.refresh(assistant_msg)

        return {
            "session_id": session_id,
            "reply": final_reply,
            "message_id": assistant_msg.id,
            "used_tools": used_tools,
            "rag_used": "search_knowledge_base" in used_tools,
        }


agent = Agent()