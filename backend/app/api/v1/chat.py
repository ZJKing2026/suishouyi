"""聊天接口：多轮对话（可选 RAG）。"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.schemas.chat import ChatSendRequest, ChatSendResponse, ChatHistoryResponse
from app.core.logging import internal_error
from app.services.chat_service import chat_service
from app.ai.llm.factory import MissingUserConfigError


router = APIRouter()


@router.post("/chat/send", response_model=ChatSendResponse, summary="发送聊天消息")
async def send_chat(
    payload: ChatSendRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        result = await chat_service.send_message(
            db=db,
            user_id=current_user.id,
            session_id=payload.session_id,
            content=payload.content,
            use_rag=getattr(payload, "use_rag", False),
        )
        return result
    except MissingUserConfigError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise internal_error("处理消息", e)


@router.get("/chat/history", response_model=ChatHistoryResponse, summary="获取会话历史")
def get_chat_history(
    session_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return chat_service.get_history(db, current_user.id, session_id)