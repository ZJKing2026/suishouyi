"""用户配置业务逻辑：读写配置、校验 Key。"""
import httpx
from sqlalchemy.orm import Session

from app.core.config import (
    DEFAULT_LLM_PROVIDER,
    DEFAULT_LLM_BASE_URL,
    DEFAULT_LLM_MODEL,
    DEFAULT_VISION_PROVIDER,
    DEFAULT_VISION_MODEL,
    DEFAULT_EMBEDDING_BASE_URL,
    DEFAULT_EMBEDDING_MODEL,
)
from app.models.user_config import UserConfig


class UserConfigService:

    def get_config(self, db: Session, user_id: int) -> UserConfig | None:
        """获取用户配置，没有则返回 None。"""
        return db.query(UserConfig).filter(UserConfig.user_id == user_id).first()

    def save_config(self, db: Session, user_id: int, data: dict) -> UserConfig:
        """保存（或更新）用户配置。"""
        config = self.get_config(db, user_id)
        if not config:
            config = UserConfig(user_id=user_id)
            db.add(config)

        # ========== 文本 AI ==========
        config.llm_provider = data.get("llm_provider", DEFAULT_LLM_PROVIDER)
        config.llm_api_key = data.get("llm_api_key", "")
        config.llm_base_url = data.get("llm_base_url", DEFAULT_LLM_BASE_URL)
        config.llm_model = data.get("llm_model", DEFAULT_LLM_MODEL)

        # ========== 视觉 AI ==========
        config.vision_provider = data.get("vision_provider", DEFAULT_VISION_PROVIDER)
        config.vision_api_key = data.get("vision_api_key", "")
        config.vision_base_url = data.get("vision_base_url", "")
        config.vision_model = data.get("vision_model", DEFAULT_VISION_MODEL)

        # ========== RAG Embedding ==========
        config.embedding_api_key = data.get("embedding_api_key", "")
        config.embedding_base_url = data.get("embedding_base_url", DEFAULT_EMBEDDING_BASE_URL)
        config.embedding_model = data.get("embedding_model", DEFAULT_EMBEDDING_MODEL)

        # ========== RAG 开关 ==========
        config.rag_enabled = data.get("rag_enabled", False)

        db.commit()
        db.refresh(config)
        return config

    def mask_key(self, key: str) -> str:
        """把 Key 打码，用于返回给前端显示。"""
        if not key:
            return ""
        if len(key) < 12:
            return "****"
        return key[:6] + "****" + key[-4:]

    # ==================== LLM Key 校验 ====================
    async def verify_key(self, api_key: str, base_url: str, model: str) -> tuple[bool, str]:
        """校验 LLM Key（文本 AI）。"""
        if not api_key or not api_key.startswith("sk-"):
            return False, "API Key 格式不对，应以 sk- 开头"

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        data = {
            "model": model,
            "messages": [{"role": "user", "content": "hi"}],
            "max_tokens": 5
        }

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.post(
                    f"{base_url}/chat/completions",
                    headers=headers,
                    json=data,
                )
            if resp.status_code == 200:
                return True, "验证成功，API Key 可用"
            elif resp.status_code == 401:
                return False, "API Key 无效"
            elif resp.status_code == 402:
                return False, "账户余额不足，请先充值"
            else:
                return False, f"请求失败: HTTP {resp.status_code}"
        except httpx.TimeoutException:
            return False, "请求超时，请检查网络或 Base URL"
        except Exception as e:
            return False, f"验证失败: {str(e)}"

    # ==================== Embedding Key 校验 ====================
    async def verify_embedding(self, api_key: str, base_url: str, model: str) -> tuple[bool, str]:
        """校验 Embedding Key（知识库向量化）。"""
        if not api_key or not api_key.startswith("sk-"):
            return False, "API Key 格式不对，应以 sk- 开头"

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        data = {
            "model": model,
            "input": ["测试文本"]
        }

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.post(
                    f"{base_url}/embeddings",
                    headers=headers,
                    json=data,
                )
            if resp.status_code == 200:
                return True, "验证成功，Embedding Key 可用"
            elif resp.status_code == 401:
                return False, "API Key 无效"
            else:
                return False, f"请求失败: HTTP {resp.status_code} - {resp.text[:200]}"
        except httpx.TimeoutException:
            return False, "请求超时"
        except Exception as e:
            return False, f"验证失败: {str(e)}"


user_config_service = UserConfigService()