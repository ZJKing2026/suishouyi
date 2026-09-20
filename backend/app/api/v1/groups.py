"""群组接口。"""
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.schemas.ai_chat import (
    CreateGroupRequest, GroupListResponse,
    SendGroupMessageRequest, GroupMessageResponse,
    GroupDetailResponse,
)
from app.schemas.agent import AgentTaskView
from app.services.group_service import group_service
from app.services.agent_service import agent_service
from app.ai.llm.factory import MissingUserConfigError

router = APIRouter()


class AddMembersRequest(BaseModel):
    member_ids: list[int]


class StartDiscussionRequest(BaseModel):
    topic: str


@router.post("/groups", summary="创建群")
def create_group(
    payload: CreateGroupRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        return group_service.create_group(db, current_user.id, payload.name, payload.member_ids)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/groups/{group_id}/members", summary="拉人进群")
def add_members(
    group_id: int,
    payload: AddMembersRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        return group_service.add_members(db, group_id, current_user.id, payload.member_ids)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/groups", response_model=GroupListResponse, summary="我的群列表")
def list_groups(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return {"groups": group_service.list_groups(db, current_user.id)}


@router.get("/groups/{group_id}", response_model=GroupDetailResponse, summary="群详情")
def get_group(
    group_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        return group_service.get_group_detail(db, group_id, current_user.id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/groups/{group_id}/send", response_model=GroupMessageResponse, summary="群发消息")
async def send_group_message(
    group_id: int,
    payload: SendGroupMessageRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        return await group_service.send_message(
            db, group_id, current_user.id, payload.content, payload.use_ai,
        )
    except MissingUserConfigError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/groups/{group_id}/ai-discussion", response_model=AgentTaskView, summary="让群里的 AI 自主讨论")
async def start_ai_discussion(
    group_id: int,
    payload: StartDiscussionRequest,
    background: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    讨论要串行调多次 LLM，可能跑几十秒。

    所以这里只建任务就返回，前端拿 task_id 轮询进度。
    """
    from app.db.session import SessionLocal

    try:
        # 先校验成员身份和人数，错误当场反馈，不用等到后台
        if not group_service._is_member(db, group_id, current_user.id):
            raise ValueError("你不是这个群的成员")
        if len(group_service._get_members(db, group_id)) < 2:
            raise ValueError("群里至少 2 个人才能讨论")

        task = agent_service.create_group_discussion(
            db, group_id, current_user.id, payload.topic,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    task_id = task["id"]

    async def run():
        # 后台任务用独立会话，请求的 db 那时已经关了
        bg_db = SessionLocal()
        try:
            await agent_service.run_group_discussion(bg_db, task_id)
        finally:
            bg_db.close()

    background.add_task(run)
    return task