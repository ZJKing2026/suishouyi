"""智能接口：语音转文字（不生成笔记）。"""
import asyncio
import uuid

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from app.core.config import UPLOAD_ROOT
from app.core.logging import get_logger
from app.api.deps import get_current_user
from app.models.user import User


logger = get_logger(__name__)

router = APIRouter()

UPLOAD_DIR = UPLOAD_ROOT / "voice"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


def _transcribe_file(path: str) -> tuple[str, int]:
    """
    同步执行 Whisper 转录（放到线程池里调用，避免阻塞事件循环）。

    参数:
        path: 音频文件的本地路径
    返回:
        (转录文本, 时长秒数)
    """
    from app.services.note_service import get_whisper_model

    model = get_whisper_model()
    segments, info = model.transcribe(
        path,
        language="zh",
        vad_filter=True,
        beam_size=5,
        initial_prompt="以下是普通话内容。",
        condition_on_previous_text=False,
    )
    text = "".join(seg.text.strip() for seg in segments)
    return text, int(info.duration or 0)


@router.post("/smart/transcribe", summary="语音转文字（不生成笔记）")
async def transcribe_audio(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
):
    """上传音频，只转录文字，不保存笔记。"""
    try:
        content = await file.read()
        if not content:
            raise HTTPException(status_code=400, detail="音频为空")

        # 保存临时文件
        ext = (file.filename or "audio.mp3").rsplit(".", 1)[-1].lower()
        stored = UPLOAD_DIR / f"{uuid.uuid4().hex}.{ext}"
        stored.write_bytes(content)

        # faster-whisper 是同步阻塞实现，丢到线程池执行
        transcript, duration = await asyncio.to_thread(_transcribe_file, str(stored))

        # 删除临时文件
        try:
            stored.unlink()
        except Exception:
            pass

        if not transcript:
            raise HTTPException(status_code=400, detail="未识别到语音内容")

        return {"text": transcript, "duration": duration}
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("语音转录失败")
        raise HTTPException(status_code=500, detail="转录失败，请稍后重试")