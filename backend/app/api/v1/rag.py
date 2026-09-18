"""RAG 接口：知识库管理 + 对话。"""
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.schemas.rag import (
    RagDocumentResponse,
    RagDocumentListResponse,
    RagAskRequest,
    RagAskResponse,
)
from app.core.logging import internal_error
from app.services.rag_service import rag_service, MissingEmbeddingConfigError
from app.ai.llm.factory import MissingUserConfigError

router = APIRouter()


@router.get("/rag/documents", response_model=RagDocumentListResponse, summary="知识库文档列表")
def list_documents(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    docs = rag_service.list_documents(db, current_user.id)
    return {"documents": docs}


@router.post("/rag/documents/upload", response_model=RagDocumentResponse, summary="上传文档到知识库")
async def upload_document(
    file: UploadFile = File(...),
    original_filename: str = Form(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        content = await file.read()
        filename = original_filename or file.filename
        doc = await rag_service.index_document(db, current_user.id, filename, content)
        return doc
    except MissingEmbeddingConfigError as e:
        raise HTTPException(status_code=428, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise internal_error("知识库处理", e)


@router.delete("/rag/documents/{doc_id}", summary="删除文档")
def delete_document(
    doc_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ok = rag_service.delete_document(db, current_user.id, doc_id)
    if not ok:
        raise HTTPException(status_code=404, detail="文档不存在")
    return {"success": True}


@router.post("/rag/ask", response_model=RagAskResponse, summary="基于知识库提问")
async def ask(
    payload: RagAskRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        result = await rag_service.ask(db, current_user.id, payload.question)
        return result
    except MissingEmbeddingConfigError as e:
        raise HTTPException(status_code=428, detail=str(e))
    except MissingUserConfigError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise internal_error("知识库处理", e)