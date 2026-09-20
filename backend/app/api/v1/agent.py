"""AI 代理任务接口：发起协商、处理请示。"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.schemas.agent import (
    PendingListResponse, ResolveRequest, AgentTaskView, StartConsultRequest,
)
from app.services.agent_service import agent_service
from app.ai.llm.factory import MissingUserConfigError

router = APIRouter()


@router.get("/agent-requests/pending", response_model=PendingListResponse, summary="待我决策的请示")
def list_pending(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    rows = agent_service.list_pending_requests(db, current_user.id)
    return {"requests": rows, "total": len(rows)}


@router.post("/agent-requests/{request_id}/resolve", response_model=AgentTaskView, summary="处理一条请示")
async def resolve_request(
    request_id: int,
    payload: ResolveRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        return await agent_service.resolve_request(
            db, request_id, current_user.id, payload.action, payload.answer,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/agent-tasks/consult", response_model=AgentTaskView, summary="让 AI 去问好友")
async def start_consult(
    payload: StartConsultRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        return await agent_service.start_peer_consult(
            db, current_user.id, payload.friend_id, payload.question,
        )
    except MissingUserConfigError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/agent-tasks/{task_id}", response_model=AgentTaskView, summary="查看任务状态")
def get_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        return agent_service.get_task_view(db, task_id, current_user.id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
