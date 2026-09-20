"""AI 请示表：AI 拿不定主意时，落一条记录等主人决策。"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from app.db.session import Base


# 请示状态
REQUEST_PENDING = "pending"
REQUEST_DECIDED = "decided"

# 用户动作
ACTION_APPROVE = "approve"     # 按 AI 建议回复
ACTION_REJECT = "reject"       # 拒绝，AI 委婉回绝对方
ACTION_CUSTOM = "custom"       # 用户自己写一句


class AgentRequest(Base):
    __tablename__ = "agent_requests"

    id = Column(Integer, primary_key=True, index=True)

    task_id = Column(Integer, ForeignKey("agent_tasks.id"), index=True)
    requester_id = Column(Integer, ForeignKey("users.id"), index=True)   # 谁的 AI 在请示
    asker_id = Column(Integer, ForeignKey("users.id"), nullable=True)    # 引起这次请示的对方
    group_id = Column(Integer, ForeignKey("groups.id"), nullable=True)

    question = Column(Text)          # 对方问的原话
    context = Column(Text, nullable=True)    # AI 查到的依据
    suggestion = Column(Text, nullable=True)  # AI 的建议回答

    status = Column(String(20), index=True, default=REQUEST_PENDING)
    action = Column(String(20), nullable=True)
    answer = Column(Text, nullable=True)     # 用户最终拍板的答复内容

    created_at = Column(DateTime, default=datetime.utcnow)
    resolved_at = Column(DateTime, nullable=True)
