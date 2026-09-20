"""好友接口。"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.schemas.friend import (
    FriendListResponse,
    InviteResponse,
    InviteDetail,
    AcceptRequest,
    SendMessageRequest,
    MessageListResponse,
    UnreadListResponse,
)
from app.services.friend_service import friend_service

router = APIRouter()


# ==================== 好友管理 ====================

@router.post("/friends/invite", response_model=InviteResponse, summary="生成邀请码")
def create_invite(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return friend_service.create_invite(db, current_user.id)


@router.get("/friends/invite/{code}", response_model=InviteDetail, summary="查看邀请详情")
def get_invite(
    code: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        return friend_service.get_invite(db, code, current_user.id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/friends/accept", summary="接受邀请")
def accept_invite(
    payload: AcceptRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        return friend_service.accept_invite(db, payload.invite_code, current_user.id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/friends", response_model=FriendListResponse, summary="好友列表")
def list_friends(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    friends = friend_service.list_friends(db, current_user.id)
    return {"friends": friends}


# ==================== 消息 ====================

@router.post("/friends/{friend_id}/send", summary="给好友发消息")
def send_message(
    friend_id: int,
    payload: SendMessageRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        return friend_service.send_message(
            db, current_user.id, friend_id, payload.content, from_ai=False,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/friends/{friend_id}/messages", response_model=MessageListResponse, summary="查看会话")
def get_messages(
    friend_id: int,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    msgs = friend_service.get_messages(db, current_user.id, friend_id, limit=limit)
    return {"messages": msgs}


@router.get("/friends/messages/unread", response_model=UnreadListResponse, summary="未读消息汇总")
def get_unread(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return friend_service.get_unread_summary(db, current_user.id)