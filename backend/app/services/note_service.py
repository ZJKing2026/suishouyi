"""语音笔记业务逻辑：音频 → 转录 → AI 摘要 → 落库。"""
import os

# 限制线程，减少内存压力
os.environ.setdefault("OPENBLAS_NUM_THREADS", "2")
os.environ.setdefault("OMP_NUM_THREADS", "2")
os.environ.setdefault("HF_ENDPOINT", "https://hf-mirror.com")

import asyncio
import uuid
from sqlalchemy.orm import Session

from app.core.config import UPLOAD_ROOT
from app.core.logging import get_logger
from app.models.note import Note
from app.ai.llm.factory import get_llm_client_for_user


logger = get_logger(__name__)

AUDIO_DIR = UPLOAD_ROOT / "audio"
AUDIO_DIR.mkdir(parents=True, exist_ok=True)

MAX_AUDIO_SIZE = 25 * 1024 * 1024
MAX_DURATION = 30 * 60

_whisper_model = None


def get_whisper_model():
    """懒加载 Whisper 模型：base 模型，平衡质量和内存。"""
    global _whisper_model
    if _whisper_model is None:
        from faster_whisper import WhisperModel
        logger.info("正在加载 Whisper base 模型...")
        _whisper_model = WhisperModel(
            "base",             # 从 tiny 升级到 base
            device="cpu",
            compute_type="int8",
            cpu_threads=2,
        )
        logger.info("Whisper base 模型加载完成")
    return _whisper_model


SUMMARY_PROMPT = """请阅读以下语音转录内容，生成一份简洁的笔记。

要求：
1. 提取一个标题（15 字以内）
2. 一句话摘要（40 字以内）
3. 3-5 个关键点

严格按以下格式输出，不要添加任何其他内容：

标题：xxxxx
摘要：xxxxx
关键点：
- xxx
- xxx
- xxx

转录内容：
---
{transcript}
---
"""


class NoteService:

    async def process_audio(
        self,
        db: Session,
        user_id: int,
        filename: str,
        content: bytes,
    ) -> Note:
        if len(content) == 0:
            raise ValueError("音频文件为空")
        if len(content) > MAX_AUDIO_SIZE:
            raise ValueError(f"音频过大（{len(content) // 1024 // 1024}MB），限制 25MB")

        ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else "mp3"
        stored_name = f"{uuid.uuid4().hex}.{ext}"
        audio_path = AUDIO_DIR / stored_name
        audio_path.write_bytes(content)

        note = Note(
            user_id=user_id,
            title="处理中...",
            audio_path=str(audio_path),
            status="transcribing",
        )
        db.add(note)
        db.commit()
        db.refresh(note)

        try:
            transcript, duration = await asyncio.to_thread(self._transcribe, str(audio_path))
            if not transcript.strip():
                raise ValueError("未识别到任何语音内容")

            note.transcript = transcript
            note.audio_duration = duration
            note.status = "summarizing"
            db.commit()
            db.refresh(note)
        except Exception as e:
            logger.exception("转录失败: %s", e)
            note.status = "failed"
            note.error_message = f"转录失败：{str(e)}"
            db.commit()
            raise

        try:
            summary_data = await self._summarize(db, user_id, transcript)
            note.title = summary_data["title"][:50]
            note.summary = summary_data["summary"]
            note.key_points = summary_data["key_points"]
            note.status = "done"
            db.commit()
            db.refresh(note)
        except Exception as e:
            logger.exception("摘要失败: %s", e)
            note.title = "（摘要失败）"
            note.status = "done"
            note.error_message = f"摘要失败：{str(e)}"
            db.commit()
            db.refresh(note)

        return note

    def _transcribe(self, audio_path: str) -> tuple[str, int]:
        """同步转录音频（由线程池调用）：返回 (文本, 时长秒数)。"""
        model = get_whisper_model()
        segments, info = model.transcribe(
            audio_path,
            language="zh",
            vad_filter=True,
            beam_size=5,                       # base 模型可以用 beam_size=5，质量更好
            initial_prompt="以下是普通话内容。",  # 提示模型是普通话
            condition_on_previous_text=False,   # 防止错误累积
        )
        texts = []
        for seg in segments:
            texts.append(seg.text.strip())
        # 中文不加空格，直接拼接
        transcript = "".join(texts)
        duration = int(info.duration) if info.duration else 0
        return transcript, duration

    async def _summarize(self, db: Session, user_id: int, transcript: str) -> dict:
        client = get_llm_client_for_user(db, user_id)
        prompt = SUMMARY_PROMPT.format(transcript=transcript[:8000])
        response = await client.chat(prompt)
        return self._parse_summary(response)

    def _parse_summary(self, text: str) -> dict:
        title = ""
        summary = ""
        key_points_lines = []
        section = None

        for line in text.split("\n"):
            line = line.strip()
            if not line:
                continue
            if line.startswith("标题："):
                title = line.replace("标题：", "").strip()
                section = "title"
            elif line.startswith("摘要："):
                summary = line.replace("摘要：", "").strip()
                section = "summary"
            elif line.startswith("关键点"):
                section = "points"
            elif line.startswith("-"):
                if section == "points":
                    key_points_lines.append(line[1:].strip())

        if not title:
            title = "语音笔记"
        if not summary:
            summary = text[:100]

        return {
            "title": title,
            "summary": summary,
            "key_points": "\n".join(f"- {p}" for p in key_points_lines),
        }

    def list_notes(self, db: Session, user_id: int) -> list[Note]:
        return (
            db.query(Note)
            .filter(Note.user_id == user_id)
            .order_by(Note.created_at.desc())
            .all()
        )

    def get_note(self, db: Session, user_id: int, note_id: int) -> Note | None:
        return (
            db.query(Note)
            .filter(Note.user_id == user_id, Note.id == note_id)
            .first()
        )

    def delete_note(self, db: Session, user_id: int, note_id: int) -> bool:
        note = self.get_note(db, user_id, note_id)
        if not note:
            return False
        try:
            if note.audio_path and os.path.exists(note.audio_path):
                os.remove(note.audio_path)
        except Exception:
            pass
        db.delete(note)
        db.commit()
        return True

    def rename_note(self, db: Session, user_id: int, note_id: int, title: str) -> Note | None:
        note = self.get_note(db, user_id, note_id)
        if note:
            note.title = title[:50]
            db.commit()
            db.refresh(note)
        return note


note_service = NoteService()