"""MCP Server 管理接口。"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.schemas.mcp import (
    McpServerCreate, McpServerUpdate, McpServerResponse,
    McpServerListResponse, McpServerTestRequest, McpServerTestResponse,
    McpToolInfo,
)
from app.core.logging import get_logger
from app.services.mcp_service import mcp_service

logger = get_logger(__name__)

router = APIRouter()


def _to_response(server) -> dict:
    tools = mcp_service.parse_cached_tools(server)
    return {
        "id": server.id,
        "name": server.name,
        "url": server.url,
        "auth_token_masked": mcp_service.mask_token(server.auth_token or ""),
        "enabled": server.enabled,
        "tool_count": len(tools),
        "tools": [
            {"name": t["name"], "description": t.get("description", ""), "input_schema": t.get("input_schema", {})}
            for t in tools
        ],
        "created_at": server.created_at,
    }


@router.get("/mcp/servers", response_model=McpServerListResponse, summary="列出 MCP Servers")
def list_servers(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    servers = mcp_service.list_servers(db, current_user.id)
    return {"servers": [_to_response(s) for s in servers]}


@router.post("/mcp/servers", response_model=McpServerResponse, summary="添加 MCP Server")
async def create_server(
    payload: McpServerCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        server = await mcp_service.create_server(
            db, current_user.id, payload.name, payload.url, payload.auth_token,
        )
        return _to_response(server)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/mcp/servers/{server_id}", response_model=McpServerResponse, summary="更新 MCP Server")
def update_server(
    server_id: int,
    payload: McpServerUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        server = mcp_service.update_server(
            db, current_user.id, server_id,
            payload.name, payload.url, payload.auth_token, payload.enabled,
        )
        return _to_response(server)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/mcp/servers/{server_id}/refresh", response_model=McpServerResponse, summary="刷新工具列表")
async def refresh_server(
    server_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    server = mcp_service.get_server(db, current_user.id, server_id)
    if not server:
        raise HTTPException(status_code=404, detail="Server 不存在")
    try:
        await mcp_service.refresh_tools(db, server)
        return _to_response(server)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/mcp/servers/{server_id}", summary="删除 MCP Server")
def delete_server(
    server_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ok = mcp_service.delete_server(db, current_user.id, server_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Server 不存在")
    return {"success": True}


@router.post("/mcp/test", response_model=McpServerTestResponse, summary="测试 MCP Server 连接")
async def test_server(payload: McpServerTestRequest):
    try:
        tools = await mcp_service.list_tools(payload.url, payload.auth_token)
        return {
            "success": True,
            "message": f"连接成功，找到 {len(tools)} 个工具",
            "tool_count": len(tools),
            "tools": [
                {"name": t["name"], "description": t.get("description", ""), "input_schema": t.get("input_schema", {})}
                for t in tools
            ],
        }
    except Exception as e:
        logger.warning("MCP 连接测试失败：%s", e)
        return {"success": False, "message": "连接失败，请检查 URL 与 Token", "tool_count": 0, "tools": []}