"""MCP 客户端：连接远程 MCP Server，拉工具列表，调用工具。"""
import json
from datetime import datetime
from typing import Any

import httpx
from sqlalchemy.orm import Session

from app.models.mcp_server import McpServer


class McpService:

    def _build_headers(self, token: str = "") -> dict:
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
        }
        if token:
            headers["Authorization"] = f"Bearer {token}"
        return headers

    async def _rpc_call(
        self,
        url: str,
        token: str,
        method: str,
        params: dict,
        timeout: float = 20.0,
    ) -> dict:
        """发一个 JSON-RPC 2.0 请求到 MCP Server。"""
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": method,
            "params": params,
        }
        headers = self._build_headers(token)

        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.post(url, headers=headers, json=payload)

        if resp.status_code != 200:
            raise ValueError(f"MCP Server 返回 HTTP {resp.status_code}: {resp.text[:200]}")

        # 尝试解析响应（可能是 JSON，也可能是 SSE）
        text = resp.text.strip()

        # SSE 格式：多行 data: 开头的
        if text.startswith("event:") or "data:" in text[:100]:
            for line in text.split("\n"):
                line = line.strip()
                if line.startswith("data:"):
                    data_str = line[5:].strip()
                    if data_str and data_str != "[DONE]":
                        try:
                            return json.loads(data_str)
                        except json.JSONDecodeError:
                            continue
            raise ValueError("无法解析 MCP 的 SSE 响应")

        # 普通 JSON
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            raise ValueError(f"MCP 响应不是合法 JSON：{text[:200]}")

    async def list_tools(self, url: str, token: str = "") -> list[dict]:
        """拉取 MCP Server 的工具列表。"""
        result = await self._rpc_call(url, token, "tools/list", {})

        if "error" in result:
            raise ValueError(f"MCP 错误：{result['error'].get('message', 'unknown')}")

        tools_raw = result.get("result", {}).get("tools", [])
        tools = []
        for t in tools_raw:
            tools.append({
                "name": t.get("name", ""),
                "description": t.get("description", ""),
                "input_schema": t.get("inputSchema") or {"type": "object", "properties": {}},
            })
        return tools

    async def call_tool(
        self,
        url: str,
        token: str,
        tool_name: str,
        arguments: dict,
    ) -> str:
        """调用 MCP Server 的某个工具，返回文本结果。"""
        result = await self._rpc_call(
            url, token, "tools/call",
            {"name": tool_name, "arguments": arguments},
        )

        if "error" in result:
            return f"错误：{result['error'].get('message', 'unknown')}"

        content = result.get("result", {}).get("content", [])
        # content 是数组，元素可能是 {type: "text", text: "..."} 或 {type: "image", ...}
        texts = []
        for item in content:
            if isinstance(item, dict):
                if item.get("type") == "text":
                    texts.append(item.get("text", ""))
                else:
                    texts.append(json.dumps(item, ensure_ascii=False)[:500])
            else:
                texts.append(str(item))

        return "\n".join(texts) if texts else "（空结果）"

    # ==================== 用户操作 ====================

    def list_servers(self, db: Session, user_id: int) -> list[McpServer]:
        return (
            db.query(McpServer)
            .filter(McpServer.user_id == user_id)
            .order_by(McpServer.created_at.desc())
            .all()
        )

    def get_server(self, db: Session, user_id: int, server_id: int) -> McpServer | None:
        return (
            db.query(McpServer)
            .filter(McpServer.user_id == user_id, McpServer.id == server_id)
            .first()
        )

    def mask_token(self, token: str) -> str:
        if not token:
            return ""
        if len(token) < 12:
            return "****"
        return token[:6] + "****" + token[-4:]

    def parse_cached_tools(self, server: McpServer) -> list[dict]:
        try:
            return json.loads(server.cached_tools or "[]")
        except json.JSONDecodeError:
            return []

    async def create_server(
        self, db: Session, user_id: int, name: str, url: str, auth_token: str,
    ) -> McpServer:
        # 先尝试连接一次，验证 URL 有效性
        try:
            tools = await self.list_tools(url, auth_token)
        except Exception as e:
            raise ValueError(f"无法连接 MCP Server：{str(e)}")

        server = McpServer(
            user_id=user_id,
            name=name,
            url=url,
            auth_token=auth_token,
            enabled=True,
            cached_tools=json.dumps(tools, ensure_ascii=False),
            cached_at=datetime.utcnow(),
        )
        db.add(server)
        db.commit()
        db.refresh(server)
        return server

    async def refresh_tools(self, db: Session, server: McpServer) -> list[dict]:
        """重新拉取工具列表并缓存。"""
        tools = await self.list_tools(server.url, server.auth_token or "")
        server.cached_tools = json.dumps(tools, ensure_ascii=False)
        server.cached_at = datetime.utcnow()
        db.commit()
        return tools

    def update_server(
        self, db: Session, user_id: int, server_id: int,
        name: str, url: str, auth_token: str, enabled: bool,
    ) -> McpServer:
        server = self.get_server(db, user_id, server_id)
        if not server:
            raise ValueError("Server 不存在")
        server.name = name
        server.url = url
        server.auth_token = auth_token
        server.enabled = enabled
        db.commit()
        db.refresh(server)
        return server

    def delete_server(self, db: Session, user_id: int, server_id: int) -> bool:
        server = self.get_server(db, user_id, server_id)
        if not server:
            return False
        db.delete(server)
        db.commit()
        return True


mcp_service = McpService()