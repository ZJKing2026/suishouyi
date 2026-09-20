"""用户资料接口格式。"""
from datetime import datetime
from pydantic import BaseModel, Field


class UpdateProfileRequest(BaseModel):
    nickname: str | None = Field(None, max_length=30)


class UserProfileResponse(BaseModel):
    id: int
    nickname: str | None
    avatar: str | None
    openid: str
    created_at: datetime

    class Config:
        from_attributes = True