"""FastAPI 应用入口。"""
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.core.config import settings
from app.api.v1.router import api_router
from app.db.session import engine, Base, SessionLocal, ensure_columns
from app.models import (
    task, file, message, user, user_config,
    session, tool, builtin_tool, note, document, mcp_server,
    friendship, user_message, ai_chat_task, group,  # noqa
    agent_task, agent_request,  # noqa
)
from app.services.market_service import seed_builtin_tools
from app.services.agent_service import agent_service


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    ensure_columns()

    db = SessionLocal()
    try:
        seed_builtin_tools(db)
        print("✅ 预置工具已就绪")

        # 上次进程中断时留下的中间态任务，这里统一收尾
        orphan = agent_service.recover_orphans(db)
        if orphan:
            print(f"⚠️ 已中断 {orphan} 个未完成的代理任务")
    finally:
        db.close()

    print(f"启动中: {settings.APP_NAME} (env={settings.APP_ENV}, mock={settings.AI_MOCK})")
    yield
    print(f"已关闭: {settings.APP_NAME}")


app = FastAPI(title=settings.APP_NAME, version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.DEBUG else [],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 静态文件：工具生成的文件
OUTPUT_DIR = Path(__file__).resolve().parent.parent / "uploads" / "output"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/static/output", StaticFiles(directory=str(OUTPUT_DIR)), name="output")

# 静态文件：用户头像
AVATAR_DIR = Path(__file__).resolve().parent.parent / "uploads" / "avatars"
AVATAR_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/static/avatars", StaticFiles(directory=str(AVATAR_DIR)), name="avatars")

app.include_router(api_router, prefix="/api/v1")


@app.get("/")
def root():
    return {"name": settings.APP_NAME, "status": "ok", "docs": "/docs"}