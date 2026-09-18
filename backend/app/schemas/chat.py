"""聊天接口的输入输出格式。"""
from datetime import datetime
from pydantic import BaseModel, Field


class ChatSendRequest(BaseModel):
    session_id: str = Field(..., description="会话 ID")
    content: str = Field(..., description="用户输入的内容")
    use_rag: bool = Field(False, description="是否启用知识库检索（保底逻辑）")


class ChatMessage(BaseModel):
    id: int
    role: str
    content: str
    created_at: datetime

    class Config:
        from_attributes = True


class ChatSendResponse(BaseModel):
    session_id: str
    reply: str
    message_id: int
    used_tools: list[str] = []
    rag_used: bool = False


class ChatHistoryResponse(BaseModel):
    session_id: str
    messages: list[ChatMessage]