from fastapi import APIRouter
from app.api.v1 import (
    health, tasks, files, chat, images, auth,
    user_config, sessions, tools, market, notes,
    tools_ext, career, rag, smart, mcp, openapi,
)

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(auth.router, tags=["auth"])
api_router.include_router(user_config.router, tags=["user_config"])
api_router.include_router(sessions.router, tags=["sessions"])
api_router.include_router(tools.router, tags=["tools"])
api_router.include_router(market.router, tags=["market"])
api_router.include_router(notes.router, tags=["notes"])
api_router.include_router(tools_ext.router, tags=["ext_tools"])
api_router.include_router(career.router, tags=["career"])
api_router.include_router(rag.router, tags=["rag"])
api_router.include_router(smart.router, tags=["smart"])
api_router.include_router(mcp.router, tags=["mcp"])
api_router.include_router(openapi.router, tags=["openapi"])
api_router.include_router(tasks.router, tags=["tasks"])
api_router.include_router(files.router, tags=["files"])
api_router.include_router(images.router, tags=["images"])
api_router.include_router(chat.router, tags=["chat"])