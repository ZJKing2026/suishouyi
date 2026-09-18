"""用户配置的接口格式。"""
from datetime import datetime
from pydantic import BaseModel, Field

from app.core.config import (
    DEFAULT_LLM_PROVIDER,
    DEFAULT_LLM_BASE_URL,
    DEFAULT_LLM_MODEL,
    DEFAULT_VISION_PROVIDER,
    DEFAULT_VISION_MODEL,
    DEFAULT_EMBEDDING_BASE_URL,
    DEFAULT_EMBEDDING_MODEL,
    DEFAULT_VISION_BASE_URL,
)


class UserConfigUpdate(BaseModel):
    llm_provider: str = Field(DEFAULT_LLM_PROVIDER)
    llm_api_key: str = Field(...)
    llm_base_url: str = Field(DEFAULT_LLM_BASE_URL)
    llm_model: str = Field(DEFAULT_LLM_MODEL)

    vision_provider: str = Field(DEFAULT_VISION_PROVIDER)
    vision_api_key: str = Field("")
    vision_base_url: str = Field(DEFAULT_VISION_BASE_URL)
    vision_model: str = Field(DEFAULT_VISION_MODEL)

    embedding_api_key: str = Field("")
    embedding_base_url: str = Field(DEFAULT_EMBEDDING_BASE_URL)
    embedding_model: str = Field(DEFAULT_EMBEDDING_MODEL)
    rag_enabled: bool = Field(False)


class UserConfigResponse(BaseModel):
    llm_provider: str
    llm_api_key_masked: str
    llm_base_url: str
    llm_model: str

    vision_provider: str
    vision_api_key_masked: str
    vision_base_url: str
    vision_model: str

    embedding_api_key_masked: str
    embedding_base_url: str
    embedding_model: str
    is_embedding_configured: bool
    rag_enabled: bool

    is_configured: bool
    updated_at: datetime


class UserConfigVerifyRequest(BaseModel):
    llm_api_key: str
    llm_base_url: str = DEFAULT_LLM_BASE_URL
    llm_model: str = DEFAULT_LLM_MODEL


class UserConfigVerifyResponse(BaseModel):
    success: bool
    message: str


class EmbeddingVerifyRequest(BaseModel):
    embedding_api_key: str
    embedding_base_url: str = DEFAULT_EMBEDDING_BASE_URL
    embedding_model: str = DEFAULT_EMBEDDING_MODEL


class EmbeddingVerifyResponse(BaseModel):
    success: bool
    message: str