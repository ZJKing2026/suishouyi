"""FastAPI 应用入口。"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.core.config import settings, DEV_JWT_SECRET, UPLOAD_ROOT
from app.core.logging import get_logger, setup_logging
from app.api.v1.router import api_router
from app.db.session import engine, Base, SessionLocal
from app.models import (
    task, file, message, user, user_config,
    session, tool, builtin_tool, note, document, mcp_server,  # noqa
)
from app.services.market_service import seed_builtin_tools


setup_logging(settings.DEBUG)
logger = get_logger(__name__)


def _check_secrets() -> None:
    """启动自检：生产环境下密钥没配就大声报警，避免带着开发默认值上线。"""
    if settings.JWT_SECRET in ("", DEV_JWT_SECRET) and settings.APP_ENV != "dev":
        logger.warning(
            "=" * 72
            + "\n[安全警告] JWT_SECRET 为空或仍是开发默认值，且 APP_ENV=%s。"
            "\n所有签发的 token 都可被伪造，请立即在 .env 中设置随机密钥。"
            "\n生成方式：python -c \"import secrets; print(secrets.token_urlsafe(48))\""
            "\n" + "=" * 72,
            settings.APP_ENV,
        )
    if not settings.INTERNAL_TOKEN and settings.APP_ENV != "dev":
        logger.warning(
            "[安全警告] INTERNAL_TOKEN 未配置，已在本次启动随机生成。"
            "多进程/多副本部署时各进程通行证不一致，内部接口会互相拒绝，请显式配置。"
        )


@asynccontextmanager
async def lifespan(app: FastAPI):
    _check_secrets()
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        seed_builtin_tools(db)
        logger.info("预置工具已就绪")
    finally:
        db.close()

    logger.info(
        "启动中: %s (env=%s, mock=%s, internal_token=%s)",
        settings.APP_NAME, settings.APP_ENV, settings.AI_MOCK,
        "已配置" if settings.INTERNAL_TOKEN else "随机生成",
    )
    yield
    logger.info("已关闭: %s", settings.APP_NAME)


app = FastAPI(
    title=settings.APP_NAME,
    version="0.1.0",
    lifespan=lifespan,
)

# allow_origins=["*"] 与 allow_credentials=True 是浏览器禁止的组合，通配时不带凭证
_cors_origins = settings.cors_origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials="*" not in _cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

OUTPUT_DIR = UPLOAD_ROOT / "output"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/static/output", StaticFiles(directory=str(OUTPUT_DIR)), name="output")

app.include_router(api_router, prefix="/api/v1")


@app.get("/")
def root():
    return {"name": settings.APP_NAME, "status": "ok", "docs": "/docs"}