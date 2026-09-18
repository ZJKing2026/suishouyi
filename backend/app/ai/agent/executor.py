"""工具执行器：内置 + 用户自定义 + MCP。"""
import json
from sqlalchemy.orm import Session

from app.ai.agent.tools import (
    BUILTIN_FUNCTIONS,
    CONTEXT_FUNCTIONS,
)
from app.services.tool_service import tool_service, execute_http_tool


async def execute_tool_async(
    db: Session,
    user_id: int,
    name: str,
    arguments_str: str,
) -> str:
    # 解析参数
    try:
        args = json.loads(arguments_str) if arguments_str else {}
    except json.JSONDecodeError:
        return f"错误：参数不是合法 JSON：{arguments_str}"

    # 1. MCP 工具（名字前缀：mcp{server_id}__{tool_name}）
    if name.startswith("mcp") and "__" in name:
        try:
            server_id_str, tool_name = name.split("__", 1)
            server_id = int(server_id_str[3:])   # 去掉 "mcp" 前缀

            from app.services.mcp_service import mcp_service
            server = mcp_service.get_server(db, user_id, server_id)
            if not server or not server.enabled:
                return f"错误：MCP Server 不存在或已禁用"

            return await mcp_service.call_tool(
                server.url, server.auth_token or "", tool_name, args,
            )
        except Exception as e:
            return f"MCP 调用失败：{str(e)}"

    # 2. 用户自定义工具
    user_tool = tool_service.get_by_name(db, user_id, name)
    if user_tool:
        return await execute_http_tool(user_tool, args)

    # 3. 需要上下文的工具
    if name in CONTEXT_FUNCTIONS:
        try:
            return await CONTEXT_FUNCTIONS[name](db, user_id, **args)
        except TypeError as e:
            return f"错误：工具参数不匹配 - {str(e)}"
        except Exception as e:
            return f"错误：{str(e)}"

    # 4. 内置同步工具
    if name in BUILTIN_FUNCTIONS:
        try:
            return str(BUILTIN_FUNCTIONS[name](**args))
        except TypeError as e:
            return f"错误：工具参数不匹配 - {str(e)}"
        except Exception as e:
            return f"错误：{str(e)}"

    return f"错误：未找到工具 '{name}'"