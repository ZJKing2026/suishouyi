"""全局配置：所有配置来自环境变量 / .env，代码中不留任何 Key。"""
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


# 项目根目录（backend/）
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# 上传文件根目录，各业务子目录由使用方自行创建
UPLOAD_ROOT = BASE_DIR / "uploads"

# 用户配置的默认值，接口层与业务层共用，避免三处各写一份
DEFAULT_LLM_PROVIDER = "deepseek"
DEFAULT_LLM_BASE_URL = "https://api.deepseek.com/v1"
DEFAULT_LLM_MODEL = "deepseek-chat"
DEFAULT_VISION_PROVIDER = "deepseek"
DEFAULT_VISION_BASE_URL = "https://api.deepseek.com/v1"
DEFAULT_VISION_MODEL = "gpt-4o-mini"
DEFAULT_EMBEDDING_BASE_URL = "https://api.siliconflow.cn/v1"
DEFAULT_EMBEDDING_MODEL = "BAAI/bge-m3"

# JWT_SECRET 留空时用来识别的开发默认值
DEV_JWT_SECRET = "dev-secret-change-in-production"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    APP_NAME: str = "随手一下"
    APP_ENV: str = "dev"
    DEBUG: bool = True
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    BACKEND_URL: str = "http://127.0.0.1:8000"

    # 跨域白名单，逗号分隔；DEBUG 下留空表示放开全部
    CORS_ORIGINS: str = ""

    DATABASE_URL: str = "sqlite:///./suishouyi.db"

    # AI（文本/对话/工具）
    AI_MOCK: bool = True
    LLM_PROVIDER: str = "deepseek"
    LLM_API_KEY: str = ""
    LLM_BASE_URL: str = "https://api.deepseek.com/v1"
    LLM_MODEL: str = "deepseek-chat"

    # 视觉模型（独立配置）
    VISION_MOCK: bool = True
    VISION_API_KEY: str = ""
    VISION_BASE_URL: str = ""
    VISION_MODEL: str = ""

    WX_APPID: str = ""
    WX_SECRET: str = ""

    JWT_SECRET: str = ""
    JWT_EXPIRE_DAYS: int = 30

    # 内部接口（邮件发送等）通行证，留空则启动时随机生成
    INTERNAL_TOKEN: str = ""

    @property
    def cors_origins(self) -> list[str]:
        """
        解析跨域白名单。

        返回:
            list[str]: 白名单列表；DEBUG 下留空表示放开全部，非 DEBUG 下留空表示不允许跨域
        """
        origins = [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]
        if origins:
            return origins
        return ["*"] if self.DEBUG else []


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()