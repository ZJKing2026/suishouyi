"""会话管理接口。"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session as DBSession

from app.db.session import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.schemas.session import (
    SessionResponse,
    SessionListResponse,
    SessionCreateRequest,
    SessionRenameRequest,
)
from app.services.session_service import session_service

router = APIRouter()


@router.get("/sessions", response_model=SessionListResponse, summary="会话列表")
def list_sessions(
    db: DBSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    sessions = session_service.list_all(db, current_user.id)
    return {"sessions": sessions}


@router.post("/sessions", response_model=SessionResponse, summary="创建新会话")
def create_session(
    payload: SessionCreateRequest,
    db: DBSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return session_service.create(db, current_user.id, payload.title)


@router.put("/sessions/{session_id}", response_model=SessionResponse, summary="重命名会话")
def rename_session(
    session_id: str,
    payload: SessionRenameRequest,
    db: DBSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    session = session_service.rename(db, current_user.id, session_id, payload.title)
    if not session:
        raise HTTPException(status_code=404, detail="会话不存在")
    return session


@router.delete("/sessions/{session_id}", summary="删除会话")
def delete_session(
    session_id: str,
    db: DBSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ok = session_service.delete(db, current_user.id, session_id)
    if not ok:
        raise HTTPException(status_code=404, detail="会话不存在")
    return {"success": True}