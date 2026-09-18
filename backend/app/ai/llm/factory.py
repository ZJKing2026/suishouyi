"""根据用户配置创建 LLM 客户端。"""
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.user_config import UserConfig
from app.ai.llm.client import LLMClient


class MissingUserConfigError(Exception):
    """用户没有配置 API Key，且平台没有开启 Mock 兜底。"""
    pass


def get_llm_client_for_user(db: Session, user_id: int) -> LLMClient:
    """
    读取用户的 API 配置，返回一个配置好的 LLMClient。
    
    优先级：
    1. 用户配置了自己的 Key → 用用户的
    2. 用户没配，但平台 AI_MOCK=true → 用 Mock 兜底
    3. 用户没配，平台也不是 Mock → 抛异常
    """
    config = db.query(UserConfig).filter(UserConfig.user_id == user_id).first()

    if config and config.llm_api_key:
        return LLMClient(
            api_key=config.llm_api_key,
            base_url=config.llm_base_url,
            model=config.llm_model,
            mock=False,
        )

    # 用户没配置，看平台是否允许 Mock 兜底
    if settings.AI_MOCK:
        return LLMClient(api_key="", base_url="", model="", mock=True)

    raise MissingUserConfigError("请先在「我的 → API 配置」中配置你的 AI Key")