"""工具接口格式。"""
from datetime import datetime
from pydantic import BaseModel, Field


class ToolCreate(BaseModel):
    name: str = Field(..., description="工具名")
    description: str = Field(..., description="描述")
    parameters_schema: str = Field(default='{"type":"object","properties":{},"required":[]}')
    api_url: str = Field(...)
    api_method: str = Field("GET")
    headers: str = Field("{}")
    body_template: str = Field("", description="POST body 模板")
    user_config: str = Field("{}", description="用户级配置")


class ToolUpdate(ToolCreate):
    enabled: bool = True


class ToolResponse(BaseModel):
    id: int
    name: str
    display_name: str = ""
    description: str
    parameters_schema: str
    api_url: str
    api_method: str
    headers: str
    body_template: str = ""
    enabled: bool
    created_at: datetime

    class Config:
        from_attributes = True


class ToolListResponse(BaseModel):
    tools: list[ToolResponse]


class ToolTestRequest(BaseModel):
    arguments: dict = Field(default_factory=dict)


class ToolTestResponse(BaseModel):
    success: bool
    result: str