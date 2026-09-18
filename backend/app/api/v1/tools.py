"""用户自定义工具接口。"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.schemas.tool import (
    ToolCreate, ToolUpdate, ToolResponse, ToolListResponse,
    ToolTestRequest, ToolTestResponse,
)
from app.services.tool_service import tool_service, execute_http_tool
from app.services.market_service import get_display_name

router = APIRouter()


def _tool_to_response(tool) -> dict:
    return {
        "id": tool.id,
        "name": tool.name,
        "display_name": get_display_name(tool.name),
        "description": tool.description,
        "parameters_schema": tool.parameters_schema,
        "api_url": tool.api_url,
        "api_method": tool.api_method,
        "headers": tool.headers,
        "body_template": tool.body_template or "",
        "enabled": tool.enabled,
        "created_at": tool.created_at,
    }


@router.get("/tools", response_model=ToolListResponse, summary="列出我的工具")
def list_tools(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    tools = tool_service.list_tools(db, current_user.id)
    return {"tools": [_tool_to_response(t) for t in tools]}


@router.post("/tools", response_model=ToolResponse, summary="创建工具")
def create_tool(
    payload: ToolCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        tool = tool_service.create_tool(db, current_user.id, payload.model_dump())
        return _tool_to_response(tool)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/tools/{tool_id}", response_model=ToolResponse, summary="更新工具")
def update_tool(
    tool_id: int,
    payload: ToolUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        tool = tool_service.update_tool(db, current_user.id, tool_id, payload.model_dump())
        return _tool_to_response(tool)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/tools/{tool_id}", summary="删除工具")
def delete_tool(
    tool_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ok = tool_service.delete_tool(db, current_user.id, tool_id)
    if not ok:
        raise HTTPException(status_code=404, detail="工具不存在")
    return {"success": True}


@router.post("/tools/{tool_id}/test", response_model=ToolTestResponse, summary="测试工具")
async def test_tool(
    tool_id: int,
    payload: ToolTestRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    tool = tool_service.get_tool(db, current_user.id, tool_id)
    if not tool:
        raise HTTPException(status_code=404, detail="工具不存在")
    result = await execute_http_tool(tool, payload.arguments)
    success = not result.startswith("错误")
    return {"success": success, "result": result}