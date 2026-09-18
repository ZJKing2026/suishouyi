"""登录接口的输入输出格式。"""
from datetime import datetime
from pydantic import BaseModel, Field


class WxLoginRequest(BaseModel):
    """小程序发来的登录请求。"""
    code: str = Field(..., description="wx.login 拿到的临时 code")
    nickname: str | None = Field(None, description="可选，用户昵称")
    avatar: str | None = Field(None, description="可选，用户头像 URL")


class UserInfo(BaseModel):
    id: int
    openid: str
    nickname: str | None
    avatar: str | None
    created_at: datetime

    class Config:
        from_attributes = True


class WxLoginResponse(BaseModel):
    """登录成功返回。"""
    token: str
    user: UserInfo