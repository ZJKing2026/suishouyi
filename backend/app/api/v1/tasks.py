"""任务接口：对外暴露的 API。"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.schemas.task import TaskCreate, TaskResponse, TaskListResponse
from app.services.task_service import task_service


router = APIRouter()


@router.post("/tasks", response_model=TaskResponse, summary="创建一个AI任务")
async def create_task(
    payload: TaskCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """用户不需要选功能，直接丢内容进来。"""
    task = await task_service.process_task(db, current_user.id, payload.content)
    return task


@router.get("/tasks", response_model=TaskListResponse, summary="获取最近的任务列表")
def list_tasks(
    limit: int = 10,
    offset: int = 0,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """查询当前用户的最近任务。"""
    return task_service.list_tasks(db, current_user.id, limit, offset)