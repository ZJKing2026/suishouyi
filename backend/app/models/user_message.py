"""用户间消息表。"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey
from app.db.session import Base


class UserMessage(Base):
    __tablename__ = "user_messages"

    id = Column(Integer, primary_key=True, index=True)
    from_user_id = Column(Integer, ForeignKey("users.id"), index=True)
    to_user_id = Column(Integer, ForeignKey("users.id"), index=True)

    content = Column(Text)
    is_read = Column(Boolean, default=False)

    # 标记：是用户直接发的，还是 AI 代理发的
    from_ai = Column(Boolean, default=False)

    # 归属的代理任务：同一对好友多次协商时，靠它区分各自的记录
    task_id = Column(Integer, ForeignKey("agent_tasks.id"), index=True, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)