"""AI 代理任务表：协商、群讨论等异步任务的统一载体。"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from app.db.session import Base


# 任务类型
TYPE_PEER_CONSULT = "peer_consult"      # 双人 AI 协商
TYPE_GROUP_DISCUSSION = "group_discussion"

# 任务状态
STATUS_RUNNING = "running"              # 正在执行
STATUS_WAITING_USER = "waiting_user"    # 卡在请示，等主人拍板
STATUS_WAITING_PEER = "waiting_peer"    # 卡在等对方 AI 执行
STATUS_DONE = "done"
STATUS_FAILED = "failed"

# 结束原因
OUTCOME_ANSWERED = "answered"
OUTCOME_DECLINED = "declined"
OUTCOME_PEER_UNAVAILABLE = "peer_unavailable"
OUTCOME_TIMEOUT = "timeout"
OUTCOME_ERROR = "error"


class AgentTask(Base):
    __tablename__ = "agent_tasks"

    id = Column(Integer, primary_key=True, index=True)

    task_type = Column(String(20), index=True)
    status = Column(String(20), index=True, default=STATUS_RUNNING)

    owner_id = Column(Integer, ForeignKey("users.id"), index=True)
    peer_id = Column(Integer, ForeignKey("users.id"), index=True, nullable=True)
    group_id = Column(Integer, ForeignKey("groups.id"), nullable=True)

    topic = Column(Text)
    payload = Column(Text, nullable=True)          # JSON：当前提问与中间上下文
    result = Column(Text, nullable=True)           # JSON：最终答复或总结
    outcome = Column(String(30), nullable=True)
    error = Column(Text, nullable=True)

    step_count = Column(Integer, default=0)        # 已执行步数，配合上限防跑飞

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    finished_at = Column(DateTime, nullable=True)
