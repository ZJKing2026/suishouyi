"""工具市场接口。"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.models.tool import Tool
from app.schemas.market import MarketListResponse
from app.schemas.tool import ToolResponse
from app.services.market_service import market_service, get_display_name

router = APIRouter()


class AddToolRequest(BaseModel):
    user_config: dict = {}


@router.get("/market/tools", response_model=MarketListResponse, summary="列出工具市场")
def list_market(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    tools = market_service.list_all(db)
    user_tool_names = [t.name for t in db.query(Tool).filter(Tool.user_id == current_user.id).all()]
    return {"tools": tools, "added_names": user_tool_names}


@router.post("/market/tools/{tool_id}/add", response_model=ToolResponse, summary="添加工具")
def add_market_tool(
    tool_id: int,
    payload: AddToolRequest = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        config = payload.user_config if payload else {}
        tool = market_service.add_to_user(db, current_user.id, tool_id, config)
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
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))