"""AI 代理任务与请示接口格式。"""
from datetime import datetime
from pydantic import BaseModel, Field


class AgentRequestItem(BaseModel):
    """一条待决策的请示。"""
    id: int
    task_id: int
    question: str
    context: str | None = None
    suggestion: str | None = None
    asker_id: int | None = None
    asker_nickname: str
    created_at: datetime


class PendingListResponse(BaseModel):
    requests: list[AgentRequestItem]
    total: int


class ResolveRequest(BaseModel):
    action: str = Field(..., description="approve / reject / custom")
    answer: str = Field("", description="action 为 custom 时必填")


class AgentTaskView(BaseModel):
    id: int
    task_type: str
    status: str
    owner_id: int
    peer_id: int | None = None
    topic: str
    outcome: str | None = None
    error: str | None = None
    result: dict = {}
    pending_request_id: int | None = None
    created_at: datetime
    finished_at: datetime | None = None


class StartConsultRequest(BaseModel):
    friend_id: int
    question: str
