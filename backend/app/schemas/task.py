"""接口输入输出的数据格式定义（Pydantic）。"""
from datetime import datetime
from pydantic import BaseModel, Field


# 用户发请求时的格式
class TaskCreate(BaseModel):
    content: str = Field(..., description="用户输入的内容，如一段文字或问题")


# 返回给前端的格式
class TaskResponse(BaseModel):
    id: int
    task_type: str
    input_text: str
    output_text: str | None
    status: str
    created_at: datetime

    class Config:
        from_attributes = True


# 追加：分页查询用的输入格式
class TaskListQuery(BaseModel):
    limit: int = 10
    offset: int = 0


# 追加：列表响应的格式（就是一个 TaskResponse 的数组）
class TaskListResponse(BaseModel):
    total: int
    items: list[TaskResponse]