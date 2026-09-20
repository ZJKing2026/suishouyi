"""好友关系表：通过邀请码建立好友。"""
import uuid
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from app.db.session import Base


class Friendship(Base):
    __tablename__ = "friendships"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True)      # 发起方
    friend_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)  # 接受方（接受前为空）

    status = Column(String(20), default="pending")   # pending / accepted / blocked
    invite_code = Column(String(32), unique=True, index=True)         # 邀请码

    created_at = Column(DateTime, default=datetime.utcnow)
    accepted_at = Column(DateTime, nullable=True)

    @staticmethod
    def generate_invite_code():
        return uuid.uuid4().hex[:16]