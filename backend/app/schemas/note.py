"""语音笔记接口格式。"""
from datetime import datetime
from pydantic import BaseModel


class NoteResponse(BaseModel):
    id: int
    title: str
    audio_duration: int
    transcript: str | None
    summary: str | None
    key_points: str | None
    status: str
    created_at: datetime

    class Config:
        from_attributes = True


class NoteListResponse(BaseModel):
    notes: list[NoteResponse]


class NoteUpdateRequest(BaseModel):
    title: str