"""求职辅助接口。"""
import uuid

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.core.config import UPLOAD_ROOT
from app.core.logging import get_logger, internal_error
from app.db.session import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.services.career_service import career_service
from app.services.file_parser import parse_file, get_extension
from app.ai.llm.factory import MissingUserConfigError

logger = get_logger(__name__)

router = APIRouter()

UPLOAD_DIR = UPLOAD_ROOT / "career"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


async def _read_file_as_text(file: UploadFile) -> str:
    """读取上传的简历文件，转成文本。"""
    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="文件为空")

    ext = get_extension(file.filename)
    stored = UPLOAD_DIR / f"{uuid.uuid4().hex}.{ext}"
    stored.write_bytes(content)

    try:
        return parse_file(str(stored), ext)
    except Exception as e:
        logger.warning("简历解析失败：%s", e)
        raise HTTPException(status_code=400, detail="文件解析失败，请确认是有效的 PDF / DOCX / TXT")


@router.post("/career/optimize_resume", summary="简历优化")
async def optimize_resume(
    resume: UploadFile = File(...),      # ← 改成 resume，和前端一致
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        text = await _read_file_as_text(resume)
        result = await career_service.optimize_resume(db, current_user.id, text)
        return {"result": result}
    except MissingUserConfigError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        raise internal_error("简历处理", e)


@router.post("/career/match_jd", summary="JD 匹配分析")
async def match_jd(
    resume: UploadFile = File(...),      # ← 改成 resume
    jd_text: str = Form(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        resume_text = await _read_file_as_text(resume)
        result = await career_service.match_jd(db, current_user.id, resume_text, jd_text)
        return {"result": result}
    except MissingUserConfigError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        raise internal_error("简历处理", e)


@router.post("/career/cover_letter", summary="生成求职信")
async def cover_letter(
    resume: UploadFile = File(...),      # ← 改成 resume
    jd_text: str = Form(...),
    company: str = Form(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        resume_text = await _read_file_as_text(resume)
        result = await career_service.generate_cover_letter(
            db, current_user.id, resume_text, jd_text, company
        )
        return {"result": result}
    except MissingUserConfigError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        raise internal_error("简历处理", e)