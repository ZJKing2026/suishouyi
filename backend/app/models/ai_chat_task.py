"""AI 自主对话任务表。"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from app.db.session import Base


class AIChatTask(Base):
    __tablename__ = "ai_chat_tasks"

    id = Column(Integer, primary_key=True, index=True)
    user_a_id = Column(Integer, ForeignKey("users.id"), index=True)
    user_b_id = Column(Integer, ForeignKey("users.id"), index=True)
    topic = Column(String(200))
    status = Column(String(20), default="running")   # running / done / failed
    max_rounds = Column(Integer, default=5)
    current_round = Column(Integer, default=0)
    summary = Column(Text, nullable=True)            # 结束后生成的总结
    created_at = Column(DateTime, default=datetime.utcnow)
    finished_at = Column(DateTime, nullable=True)