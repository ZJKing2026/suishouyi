"""MCP Server 表：用户接入的 MCP 服务器。"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey
from app.db.session import Base


class McpServer(Base):
    __tablename__ = "mcp_servers"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True)

    name = Column(String(64))                  # 用户给这个 Server 起的名字
    url = Column(String(500))                  # MCP Server 的 HTTP 端点
    auth_token = Column(String(500), default="")   # 可选：Bearer token
    enabled = Column(Boolean, default=True)

    # 缓存工具列表（JSON 字符串），避免每次都去 Server 拉
    cached_tools = Column(Text, default="[]")
    cached_at = Column(DateTime, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)