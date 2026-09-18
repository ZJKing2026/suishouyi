"""会话接口格式。"""
from datetime import datetime
from pydantic import BaseModel


class SessionResponse(BaseModel):
    id: str
    title: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class SessionListResponse(BaseModel):
    sessions: list[SessionResponse]


class SessionCreateRequest(BaseModel):
    title: str = "新对话"


class SessionRenameRequest(BaseModel):
    title: str