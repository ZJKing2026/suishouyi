"""RAG 接口格式。"""
from datetime import datetime
from pydantic import BaseModel, Field


class RagDocumentResponse(BaseModel):
    id: int
    filename: str
    file_type: str
    file_size: int
    chunk_count: int
    status: str
    error_message: str | None
    created_at: datetime

    class Config:
        from_attributes = True


class RagDocumentListResponse(BaseModel):
    documents: list[RagDocumentResponse]


class RagAskRequest(BaseModel):
    question: str = Field(..., description="基于知识库的问题")


class RagSource(BaseModel):
    content: str
    similarity: float
    document_id: int


class RagAskResponse(BaseModel):
    answer: str
    sources: list[RagSource]