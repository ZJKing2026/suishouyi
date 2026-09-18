"""图片业务逻辑：保存图片 → 视觉模型 → 落库（含 task 记录）。"""
import uuid

from sqlalchemy.orm import Session

from app.core.config import UPLOAD_ROOT
from app.models.file import FileRecord
from app.models.task import Task
from app.ai.vision.factory import get_vision_client_for_user
from app.services.file_parser import get_extension


UPLOAD_DIR = UPLOAD_ROOT
UPLOAD_DIR.mkdir(exist_ok=True)

SUPPORTED_IMAGE_TYPES = {"jpg", "jpeg", "png", "gif", "webp"}
MAX_IMAGE_SIZE = 10 * 1024 * 1024


class ImageService:
    async def save_and_process(
        self, db: Session, user_id: int, filename: str, content: bytes,
        prompt: str = "请描述这张图片的内容",
    ) -> dict:
        ext = get_extension(filename)
        if ext not in SUPPORTED_IMAGE_TYPES:
            raise ValueError(f"不支持的图片类型")

        file_size = len(content)
        if file_size == 0:
            raise ValueError("上传的是空图片")
        if file_size > MAX_IMAGE_SIZE:
            raise ValueError(f"图片过大（{file_size // 1024}KB），限制 10MB")

        stored_name = f"{uuid.uuid4().hex}.{ext}"
        storage_path = UPLOAD_DIR / stored_name
        storage_path.write_bytes(content)

        # 1. 保存图片记录
        file_record = FileRecord(
            user_id=user_id, filename=filename, stored_name=stored_name,
            file_type=ext, file_size=file_size, storage_path=str(storage_path),
            status="uploaded",
        )
        db.add(file_record)
        db.commit()
        db.refresh(file_record)

        # 2. 创建 task 记录
        task = Task(
            user_id=user_id,
            task_type="image_description",
            input_text=f"图片：《{filename}》",
            status="processing",
        )
        db.add(task)
        db.commit()
        db.refresh(task)

        # 3. 视觉处理
        try:
            client = get_vision_client_for_user(db, user_id)
            description = await client.describe_image(str(storage_path), prompt)

            file_record.parsed_text = description
            file_record.status = "parsed"
            db.commit()

            task.output_text = description
            task.status = "done"
            db.commit()
            db.refresh(task)
        except Exception as e:
            file_record.status = "failed"
            task.status = "failed"
            task.output_text = f"处理失败: {str(e)}"
            db.commit()
            raise ValueError(f"图片处理失败: {str(e)}")

        return {
            "file": file_record,
            "task_type": "image_description",
            "ai_output": description,
        }


image_service = ImageService()