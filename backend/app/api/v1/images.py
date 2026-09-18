"""图片接口：拍照/选图 → AI 理解。"""
from fastapi import APIRouter, Depends, File, UploadFile, HTTPException, Form
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.schemas.file import FileProcessResponse
from app.core.logging import internal_error
from app.services.image_service import image_service


router = APIRouter()


@router.post(
    "/images/upload",
    response_model=FileProcessResponse,
    summary="上传图片并自动AI理解",
)
async def upload_image(
    file: UploadFile = File(...),
    original_filename: str = Form(None),
    prompt: str = Form("请描述这张图片的内容"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        content = await file.read()
        filename = original_filename or file.filename

        result = await image_service.save_and_process(
            db=db,
            user_id=current_user.id,
            filename=filename,
            content=content,
            prompt=prompt,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise internal_error("图片处理", e)