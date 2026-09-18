"""语音笔记接口。"""
from fastapi import APIRouter, Depends, File, UploadFile, HTTPException, Form
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.schemas.note import (
    NoteResponse,
    NoteListResponse,
    NoteUpdateRequest,
)
from app.core.logging import internal_error
from app.services.note_service import note_service

router = APIRouter()


@router.post("/notes/upload", response_model=NoteResponse, summary="上传音频，生成笔记")
async def upload_audio(
    file: UploadFile = File(...),
    original_filename: str = Form(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    上传录音文件 → 转文字 → AI 摘要 → 保存为笔记。
    """
    try:
        content = await file.read()
        filename = original_filename or file.filename

        note = await note_service.process_audio(
            db=db,
            user_id=current_user.id,
            filename=filename,
            content=content,
        )
        return note
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise internal_error("音频处理", e)


@router.get("/notes", response_model=NoteListResponse, summary="笔记列表")
def list_notes(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    notes = note_service.list_notes(db, current_user.id)
    return {"notes": notes}


@router.get("/notes/{note_id}", response_model=NoteResponse, summary="笔记详情")
def get_note(
    note_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    note = note_service.get_note(db, current_user.id, note_id)
    if not note:
        raise HTTPException(status_code=404, detail="笔记不存在")
    return note


@router.put("/notes/{note_id}", response_model=NoteResponse, summary="重命名笔记")
def rename_note(
    note_id: int,
    payload: NoteUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    note = note_service.rename_note(db, current_user.id, note_id, payload.title)
    if not note:
        raise HTTPException(status_code=404, detail="笔记不存在")
    return note


@router.delete("/notes/{note_id}", summary="删除笔记")
def delete_note(
    note_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ok = note_service.delete_note(db, current_user.id, note_id)
    if not ok:
        raise HTTPException(status_code=404, detail="笔记不存在")
    return {"success": True}