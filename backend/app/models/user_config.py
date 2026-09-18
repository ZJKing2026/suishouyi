"""用户配置表：存储每个用户自己的 API Key 配置。"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean
from app.core.config import (
    DEFAULT_LLM_PROVIDER,
    DEFAULT_LLM_BASE_URL,
    DEFAULT_LLM_MODEL,
    DEFAULT_VISION_PROVIDER,
    DEFAULT_VISION_MODEL,
    DEFAULT_EMBEDDING_BASE_URL,
    DEFAULT_EMBEDDING_MODEL,
)
from app.db.session import Base


class UserConfig(Base):
    __tablename__ = "user_configs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, index=True)

    # ========== 文本 AI ==========
    llm_provider = Column(String(32), default=DEFAULT_LLM_PROVIDER)
    llm_api_key = Column(String(256), default="")
    llm_base_url = Column(String(256), default=DEFAULT_LLM_BASE_URL)
    llm_model = Column(String(64), default=DEFAULT_LLM_MODEL)

    # ========== 视觉 AI ==========
    vision_provider = Column(String(32), default=DEFAULT_VISION_PROVIDER)
    vision_api_key = Column(String(256), default="")
    vision_base_url = Column(String(256), default="")
    vision_model = Column(String(64), default=DEFAULT_VISION_MODEL)

    # ========== RAG Embedding ==========
    embedding_api_key = Column(String(256), default="")
    embedding_base_url = Column(String(256), default=DEFAULT_EMBEDDING_BASE_URL)
    embedding_model = Column(String(64), default=DEFAULT_EMBEDDING_MODEL)

    # ========== RAG 开关（用户级） ==========
    rag_enabled = Column(Boolean, default=False)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
