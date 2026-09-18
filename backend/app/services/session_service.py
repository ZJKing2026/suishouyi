"""会话业务逻辑。"""
import uuid
from sqlalchemy.orm import Session as DBSession

from app.models.session import Session


class SessionService:

    def create(self, db: DBSession, user_id: int, title: str = "新对话") -> Session:
        """创建新会话。"""
        session = Session(
            id=uuid.uuid4().hex,
            user_id=user_id,
            title=title,
        )
        db.add(session)
        db.commit()
        db.refresh(session)
        return session

    def list_all(self, db: DBSession, user_id: int) -> list[Session]:
        """列出用户的所有会话（最新的在前）。"""
        return (
            db.query(Session)
            .filter(Session.user_id == user_id)
            .order_by(Session.updated_at.desc())
            .all()
        )

    def get(self, db: DBSession, user_id: int, session_id: str) -> Session | None:
        return (
            db.query(Session)
            .filter(Session.user_id == user_id, Session.id == session_id)
            .first()
        )

    def ensure(self, db: DBSession, user_id: int, session_id: str) -> Session:
        """确保会话存在，不存在就创建。"""
        session = self.get(db, user_id, session_id)
        if not session:
            session = Session(
                id=session_id,
                user_id=user_id,
                title="新对话",
            )
            db.add(session)
            db.commit()
            db.refresh(session)
        return session

    def touch(self, db: DBSession, session_id: str):
        """更新会话的最后活跃时间。"""
        from datetime import datetime
        session = db.query(Session).filter(Session.id == session_id).first()
        if session:
            session.updated_at = datetime.utcnow()
            db.commit()

    def rename(self, db: DBSession, user_id: int, session_id: str, title: str) -> Session | None:
        session = self.get(db, user_id, session_id)
        if session:
            session.title = title[:50]
            db.commit()
            db.refresh(session)
        return session

    def delete(self, db: DBSession, user_id: int, session_id: str) -> bool:
        session = self.get(db, user_id, session_id)
        if not session:
            return False
        db.delete(session)
        db.commit()
        return True


session_service = SessionService()