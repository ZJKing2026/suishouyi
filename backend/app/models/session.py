"""会话表：管理每个用户的多次对话。"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from app.db.session import Base


class Session(Base):
    __tablename__ = "sessions"

    id = Column(String(64), primary_key=True)             # session_id（UUID 字符串）
    user_id = Column(Integer, ForeignKey("users.id"), index=True)
    title = Column(String(100), default="新对话")          # 会话标题
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)