"""好友接口格式。"""
from datetime import datetime
from pydantic import BaseModel, Field


# ==================== 好友 ====================

class FriendResponse(BaseModel):
    id: int
    friend_id: int
    nickname: str
    avatar: str | None = None
    status: str
    created_at: datetime


class FriendListResponse(BaseModel):
    friends: list[FriendResponse]


class InviteResponse(BaseModel):
    invite_code: str
    share_path: str


class InviteDetail(BaseModel):
    inviter_nickname: str
    inviter_avatar: str | None = None
    status: str
    is_self: bool


class AcceptRequest(BaseModel):
    invite_code: str


# ==================== 消息 ====================

class SendMessageRequest(BaseModel):
    content: str = Field(..., description="消息内容")


class MessageResponse(BaseModel):
    id: int
    from_user_id: int
    to_user_id: int
    content: str
    is_read: bool
    from_ai: bool
    created_at: datetime

    class Config:
        from_attributes = True


class MessageListResponse(BaseModel):
    messages: list[MessageResponse]


class UnreadSummary(BaseModel):
    """未读消息汇总：某个好友给我发了几条。"""
    from_user_id: int
    nickname: str
    unread_count: int
    last_content: str
    last_time: datetime


class UnreadListResponse(BaseModel):
    summaries: list[UnreadSummary]
    total_unread: int