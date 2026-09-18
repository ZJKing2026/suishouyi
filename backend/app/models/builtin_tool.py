"""内置工具市场表。"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime
from app.db.session import Base


class BuiltinTool(Base):
    __tablename__ = "builtin_tools"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(64), unique=True, index=True)
    description = Column(String(500))
    category = Column(String(32), default="其他")
    icon = Column(String(16), default="🔧")
    parameters_schema = Column(Text)
    api_url = Column(String(500))
    api_method = Column(String(10), default="GET")
    headers = Column(Text, default="{}")
    body_template = Column(Text, default="")            # 新增
    user_config_schema = Column(Text, default="{}")     # 新增：告诉前端需要用户填什么
    enabled = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)