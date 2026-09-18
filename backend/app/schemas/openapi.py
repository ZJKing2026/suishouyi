"""OpenAPI 导入接口格式。"""
from pydantic import BaseModel, Field


class OpenApiParseRequest(BaseModel):
    """解析请求。"""
    source_type: str = Field("text", description="'text' 或 'url'")
    content: str = Field(..., description="JSON 内容或 URL")


class ParsedTool(BaseModel):
    name: str
    description: str
    api_url: str
    api_method: str
    parameters_schema: str


class OpenApiParseResponse(BaseModel):
    success: bool
    message: str
    tools: list[ParsedTool] = []


class OpenApiImportRequest(BaseModel):
    """导入请求。"""
    tools: list[ParsedTool]
    prefix: str = Field("", description="工具名前缀，避免冲突")


class OpenApiImportResponse(BaseModel):
    success: bool
    created: int
    skipped: int
    created_names: list[str] = []
    skipped_names: list[str] = []