"""根据用户配置创建视觉客户端。"""
from sqlalchemy.orm import Session

from app.core.config import settings, DEFAULT_VISION_MODEL
from app.models.user_config import UserConfig
from app.ai.vision.client import VisionClient


class MissingUserConfigError(Exception):
    pass


def get_vision_client_for_user(db: Session, user_id: int) -> VisionClient:
    """
    读取用户视觉配置，返回 VisionClient。
    若用户没填独立视觉 Key，则回退用文本的 Key 和 Base URL。
    """
    config = db.query(UserConfig).filter(UserConfig.user_id == user_id).first()

    if not config or not config.llm_api_key:
        if settings.AI_MOCK:
            return VisionClient(api_key="", base_url="", model="", mock=True)
        raise MissingUserConfigError("请先在「我的 → API 配置」中配置你的 AI Key")

    # 视觉独立 Key 优先，没有就回退到文本的
    vision_key = config.vision_api_key or config.llm_api_key
    vision_url = config.vision_base_url or config.llm_base_url
    vision_model = config.vision_model or DEFAULT_VISION_MODEL

    return VisionClient(
        api_key=vision_key,
        base_url=vision_url,
        model=vision_model,
        mock=False,
    )