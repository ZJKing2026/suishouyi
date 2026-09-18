"""文件数据表模型：记录用户上传的每个文件。"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey
from app.db.session import Base


class FileRecord(Base):
    __tablename__ = "files"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True)   # ← 新增
    filename = Column(String(255))
    stored_name = Column(String(255))
    file_type = Column(String(20))
    file_size = Column(Integer)
    storage_path = Column(String(500))
    parsed_text = Column(Text, nullable=True)
    status = Column(String(20), default="uploaded")
    created_at = Column(DateTime, default=datetime.utcnow)