"""文件上传接口：接收文件 → 自动解析 → 自动 AI 处理。"""
from fastapi import APIRouter, Depends, File, UploadFile, HTTPException, Form
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.schemas.file import FileProcessResponse
from app.core.logging import internal_error
from app.services.file_service import file_service


router = APIRouter()


@router.post(
    "/files/upload",
    response_model=FileProcessResponse,
    summary="上传文件并自动AI处理",
)
async def upload_file(
    file: UploadFile = File(...),
    original_filename: str = Form(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        content = await file.read()
        filename = original_filename or file.filename

        result = await file_service.save_and_process(
            db=db,
            user_id=current_user.id,
            filename=filename,
            content=content,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise internal_error("文件处理", e)