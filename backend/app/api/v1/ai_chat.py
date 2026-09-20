"""AI 自主对话接口。"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.schemas.ai_chat import StartAIChatRequest, AIChatTaskResponse
from app.services.ai_chat_service import ai_chat_service
from app.ai.llm.factory import MissingUserConfigError

router = APIRouter()


@router.post("/ai-chat/start", response_model=AIChatTaskResponse, summary="启动 AI 自主对话")
async def start_ai_chat(
    payload: StartAIChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    启动一次 AI 自主对话。
    AI 会自己判断何时结束，无需用户指定轮数。
    """
    try:
        return await ai_chat_service.start_chat(
            db,
            current_user.id,
            payload.friend_id,
            payload.topic,
        )
    except MissingUserConfigError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"启动失败：{str(e)}")


@router.get("/ai-chat/{task_id}", response_model=AIChatTaskResponse, summary="查看对话任务")
def get_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        return ai_chat_service.get_task(db, current_user.id, task_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))