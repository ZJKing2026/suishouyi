"""OpenAPI 导入接口。"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.schemas.openapi import (
    OpenApiParseRequest, OpenApiParseResponse,
    OpenApiImportRequest, OpenApiImportResponse,
    ParsedTool,
)
from app.core.logging import internal_error
from app.services.openapi_service import openapi_service

router = APIRouter()


@router.post("/openapi/parse", response_model=OpenApiParseResponse, summary="解析 OpenAPI 文档")
async def parse_openapi(
    payload: OpenApiParseRequest,
    current_user: User = Depends(get_current_user),
):
    """解析 OpenAPI JSON，返回可导入的工具列表。"""
    try:
        if payload.source_type == "url":
            spec = await openapi_service.fetch_spec_from_url(payload.content.strip())
            tools = await openapi_service.parse_spec(spec, payload.content.strip())
        else:
            tools = await openapi_service.parse_spec(payload.content)

        return {
            "success": True,
            "message": f"成功解析出 {len(tools)} 个工具",
            "tools": tools,
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise internal_error("解析 OpenAPI", e)


@router.post("/openapi/import", response_model=OpenApiImportResponse, summary="导入 OpenAPI 工具")
def import_openapi(
    payload: OpenApiImportRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """批量创建工具。"""
    try:
        tools_data = [t.model_dump() for t in payload.tools]
        result = openapi_service.import_tools(
            db, current_user.id, tools_data, payload.prefix,
        )
        return {"success": True, **result}
    except Exception as e:
        raise internal_error("导入工具", e)