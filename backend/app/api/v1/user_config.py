"""用户配置接口：读写 + 验证 Key。"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.config import (
    DEFAULT_LLM_PROVIDER,
    DEFAULT_LLM_BASE_URL,
    DEFAULT_LLM_MODEL,
    DEFAULT_VISION_PROVIDER,
    DEFAULT_VISION_BASE_URL,
    DEFAULT_VISION_MODEL,
    DEFAULT_EMBEDDING_BASE_URL,
    DEFAULT_EMBEDDING_MODEL,
)
from app.db.session import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.schemas.user_config import (
    UserConfigUpdate,
    UserConfigResponse,
    UserConfigVerifyRequest,
    UserConfigVerifyResponse,
    EmbeddingVerifyRequest,
    EmbeddingVerifyResponse,
)
from app.services.user_config_service import user_config_service

router = APIRouter()


def _to_response(config, user) -> dict:
    """把 UserConfig 对象组装成响应。没有配置时返回默认值。"""
    if not config:
        return {
            "llm_provider": DEFAULT_LLM_PROVIDER,
            "llm_api_key_masked": "",
            "llm_base_url": DEFAULT_LLM_BASE_URL,
            "llm_model": DEFAULT_LLM_MODEL,
            "vision_provider": DEFAULT_VISION_PROVIDER,
            "vision_api_key_masked": "",
            "vision_base_url": DEFAULT_VISION_BASE_URL,
            "vision_model": DEFAULT_VISION_MODEL,
            "embedding_api_key_masked": "",
            "embedding_base_url": DEFAULT_EMBEDDING_BASE_URL,
            "embedding_model": DEFAULT_EMBEDDING_MODEL,
            "is_embedding_configured": False,
            "rag_enabled": False,
            "is_configured": False,
            "updated_at": user.created_at,
        }

    return {
        # 文本 AI
        "llm_provider": config.llm_provider,
        "llm_api_key_masked": user_config_service.mask_key(config.llm_api_key),
        "llm_base_url": config.llm_base_url,
        "llm_model": config.llm_model,

        # 视觉 AI
        "vision_provider": config.vision_provider,
        "vision_api_key_masked": user_config_service.mask_key(config.vision_api_key or ""),
        "vision_base_url": config.vision_base_url or config.llm_base_url,
        "vision_model": config.vision_model,

        # Embedding
        "embedding_api_key_masked": user_config_service.mask_key(config.embedding_api_key or ""),
        "embedding_base_url": config.embedding_base_url or DEFAULT_EMBEDDING_BASE_URL,
        "embedding_model": config.embedding_model or DEFAULT_EMBEDDING_MODEL,
        "is_embedding_configured": bool(config.embedding_api_key),

        # RAG 开关
        "rag_enabled": bool(config.rag_enabled),

        # 总状态
        "is_configured": bool(config.llm_api_key),
        "updated_at": config.updated_at,
    }


@router.get("/user/config", response_model=UserConfigResponse, summary="获取用户配置")
def get_user_config(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """返回当前用户的配置（Key 会打码）。"""
    config = user_config_service.get_config(db, current_user.id)
    return _to_response(config, current_user)


@router.put("/user/config", response_model=UserConfigResponse, summary="保存用户配置")
def update_user_config(
    payload: UserConfigUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """保存用户自己的 API 配置。"""
    config = user_config_service.save_config(db, current_user.id, payload.model_dump())
    return _to_response(config, current_user)


@router.post(
    "/user/config/verify",
    response_model=UserConfigVerifyResponse,
    summary="验证 LLM Key 是否有效",
)
async def verify_user_config(payload: UserConfigVerifyRequest):
    """用户填完 Key，点"测试文本连接"，后端发一个最小请求验证。"""
    success, message = await user_config_service.verify_key(
        api_key=payload.llm_api_key,
        base_url=payload.llm_base_url,
        model=payload.llm_model,
    )
    return {"success": success, "message": message}


@router.post(
    "/user/config/verify_embedding",
    response_model=EmbeddingVerifyResponse,
    summary="验证 Embedding Key 是否有效",
)
async def verify_embedding(payload: EmbeddingVerifyRequest):
    """用户填完 Embedding Key，点"测试 Embedding 连接"，后端验证。"""
    success, message = await user_config_service.verify_embedding(
        api_key=payload.embedding_api_key,
        base_url=payload.embedding_base_url,
        model=payload.embedding_model,
    )
    return {"success": success, "message": message}