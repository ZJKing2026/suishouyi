"""聊天业务逻辑。"""
from sqlalchemy.orm import Session

from app.models.message import Message
from app.ai.agent.agent import agent


class ChatService:
    async def send_message(
        self,
        db: Session,
        user_id: int,
        session_id: str,
        content: str,
        use_rag: bool = False,
    ) -> dict:
        return await agent.run(db, user_id, session_id, content, use_rag=use_rag)

    def get_history(self, db: Session, user_id: int, session_id: str) -> dict:
        messages = (
            db.query(Message)
            .filter(Message.user_id == user_id, Message.session_id == session_id)
            .order_by(Message.created_at.asc())
            .all()
        )
        return {"session_id": session_id, "messages": messages}


chat_service = ChatService()