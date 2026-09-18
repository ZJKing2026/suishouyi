"""认证接口：微信登录。"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.auth import WxLoginRequest, WxLoginResponse
from app.core.logging import internal_error
from app.services.auth_service import auth_service

router = APIRouter()


@router.post("/auth/wx-login", response_model=WxLoginResponse, summary="微信登录")
async def wx_login(
    payload: WxLoginRequest,
    db: Session = Depends(get_db),
):
    """
    小程序调用 wx.login() 拿到 code，发到这里换取 token。
    用户不存在会自动创建。
    """
    try:
        result = await auth_service.wx_login(
            db=db,
            code=payload.code,
            nickname=payload.nickname,
            avatar=payload.avatar,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise internal_error("微信登录", e)