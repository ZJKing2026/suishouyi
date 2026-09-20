"""AI 自主对话 + 群聊接口格式。"""
from datetime import datetime
from pydantic import BaseModel


# ==================== AI 自主对话 ====================

class StartAIChatRequest(BaseModel):
    friend_id: int
    topic: str
    # 注意：不再有 max_rounds 参数，AI 自己判断何时结束


class AIChatLogItem(BaseModel):
    speaker: str              # "a" / "b"
    content: str
    round_num: int
    created_at: datetime

    class Config:
        from_attributes = True


class AIChatTaskResponse(BaseModel):
    id: int
    user_a_id: int
    user_b_id: int
    topic: str
    status: str
    current_round: int
    max_rounds: int           # 现在是"安全上限"，不是用户设定
    summary: str | None
    logs: list[AIChatLogItem] = []
    created_at: datetime


# ==================== 群聊 ====================

class CreateGroupRequest(BaseModel):
    name: str
    member_ids: list[int]


class GroupResponse(BaseModel):
    id: int
    name: str
    owner_id: int
    member_count: int
    created_at: datetime


class GroupListResponse(BaseModel):
    groups: list[GroupResponse]


class GroupMessageResponse(BaseModel):
    id: int
    group_id: int
    from_user_id: int
    from_nickname: str
    content: str
    from_ai: bool
    created_at: datetime


class SendGroupMessageRequest(BaseModel):
    content: str
    use_ai: bool = False


class GroupDetailResponse(BaseModel):
    group: GroupResponse
    members: list[dict]
    messages: list[GroupMessageResponse]