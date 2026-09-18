"""语音笔记表：存储用户录制的音频、转录文字、AI 摘要。"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from app.db.session import Base


class Note(Base):
    __tablename__ = "notes"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True)

    title = Column(String(100), default="新笔记")     # 标题（自动生成）
    audio_path = Column(String(500))                  # 音频文件路径
    audio_duration = Column(Integer, default=0)       # 音频时长（秒）

    transcript = Column(Text, nullable=True)          # 转录的原文
    summary = Column(Text, nullable=True)             # AI 摘要
    key_points = Column(Text, nullable=True)          # 关键点（JSON 数组字符串）

    status = Column(String(20), default="pending")    # pending / transcribing / done / failed
    error_message = Column(Text, nullable=True)       # 失败原因

    created_at = Column(DateTime, default=datetime.utcnow)