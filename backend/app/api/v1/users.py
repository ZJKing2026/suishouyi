"""用户资料接口：获取、改昵称、上传头像。"""
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.schemas.user import UpdateProfileRequest, UserProfileResponse

router = APIRouter()

AVATAR_DIR = Path(__file__).resolve().parent.parent.parent.parent / "uploads" / "avatars"
AVATAR_DIR.mkdir(parents=True, exist_ok=True)

ALLOWED_AVATAR_TYPES = {"jpg", "jpeg", "png", "webp", "gif"}
MAX_AVATAR_SIZE = 5 * 1024 * 1024  # 5MB


@router.get("/users/me", response_model=UserProfileResponse, summary="获取我的资料")
def get_me(current_user: User = Depends(get_current_user)):
    return current_user


@router.put("/users/me", response_model=UserProfileResponse, summary="修改昵称")
def update_me(
    payload: UpdateProfileRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if payload.nickname is not None:
        nickname = payload.nickname.strip()
        if not nickname:
            raise HTTPException(status_code=400, detail="昵称不能为空")
        if len(nickname) > 30:
            raise HTTPException(status_code=400, detail="昵称不能超过 30 字")
        current_user.nickname = nickname
        db.commit()
        db.refresh(current_user)
    return current_user


@router.post("/users/me/avatar", response_model=UserProfileResponse, summary="上传头像")
async def upload_avatar(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ext = (file.filename or "avatar.jpg").rsplit(".", 1)[-1].lower()
    if ext not in ALLOWED_AVATAR_TYPES:
        raise HTTPException(status_code=400, detail="头像仅支持 jpg / png / webp / gif")

    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="文件为空")
    if len(content) > MAX_AVATAR_SIZE:
        raise HTTPException(status_code=400, detail="头像过大，限制 5MB")

    stored_name = f"{uuid.uuid4().hex}.{ext}"
    (AVATAR_DIR / stored_name).write_bytes(content)

    current_user.avatar = f"/static/avatars/{stored_name}"
    db.commit()
    db.refresh(current_user)
    return current_user