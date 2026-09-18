"""用户表：存储微信用户基本信息。"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime
from app.db.session import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    openid = Column(String(64), unique=True, index=True)   # 微信唯一标识
    nickname = Column(String(64), nullable=True)
    avatar = Column(String(500), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)