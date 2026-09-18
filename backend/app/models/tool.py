"""用户自定义工具表。"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey
from app.db.session import Base


class Tool(Base):
    __tablename__ = "tools"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True)

    name = Column(String(64))
    description = Column(String(500))
    parameters_schema = Column(Text)

    api_url = Column(String(500))
    api_method = Column(String(10), default="GET")
    headers = Column(Text, default="{}")

    # 新增：POST body 模板（如 {"msg_type":"text","content":{"text":"{message}"}}）
    body_template = Column(Text, default="")

    # 新增：用户级配置（如 {"webhook_url": "https://...", "email": "xx@qq.com"}）
    user_config = Column(Text, default="{}")

    enabled = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)