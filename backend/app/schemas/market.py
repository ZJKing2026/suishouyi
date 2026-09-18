"""工具市场接口格式。"""
from pydantic import BaseModel


class BuiltinToolResponse(BaseModel):
    id: int
    name: str
    display_name: str
    description: str
    category: str
    icon: str
    parameters_schema: str
    api_url: str
    api_method: str
    user_config_schema: str = "{}"

    class Config:
        from_attributes = True


class MarketListResponse(BaseModel):
    tools: list[BuiltinToolResponse]
    added_names: list[str]