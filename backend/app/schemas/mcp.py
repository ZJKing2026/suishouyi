"""MCP 接口格式。"""
from datetime import datetime
from pydantic import BaseModel, Field


class McpServerCreate(BaseModel):
    name: str = Field(..., description="Server 名字，如 '文件系统工具'")
    url: str = Field(..., description="MCP Server 的 HTTP 端点 URL")
    auth_token: str = Field("", description="可选 Bearer Token")


class McpServerUpdate(BaseModel):
    name: str
    url: str
    auth_token: str = ""
    enabled: bool = True


class McpToolInfo(BaseModel):
    name: str
    description: str
    input_schema: dict = {}


class McpServerResponse(BaseModel):
    id: int
    name: str
    url: str
    auth_token_masked: str
    enabled: bool
    tool_count: int
    tools: list[McpToolInfo] = []
    created_at: datetime


class McpServerListResponse(BaseModel):
    servers: list[McpServerResponse]


class McpServerTestRequest(BaseModel):
    url: str
    auth_token: str = ""


class McpServerTestResponse(BaseModel):
    success: bool
    message: str
    tool_count: int = 0
    tools: list[McpToolInfo] = []