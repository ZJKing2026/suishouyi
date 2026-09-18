"""文件业务逻辑：保存 → 解析 → 自动索引到知识库 → AI 处理。"""
import uuid

from sqlalchemy.orm import Session

from app.core.config import UPLOAD_ROOT
from app.core.logging import get_logger
from app.models.file import FileRecord
from app.models.task import Task
from app.models.user_config import UserConfig
from app.services.file_parser import parse_file, get_extension, is_supported, MAX_FILE_SIZE
from app.ai.router.router import ai_router


logger = get_logger(__name__)

UPLOAD_DIR = UPLOAD_ROOT
UPLOAD_DIR.mkdir(exist_ok=True)


class FileService:
    async def save_and_process(
        self, db: Session, user_id: int, filename: str, content: bytes,
    ) -> dict:
        if not is_supported(filename):
            raise ValueError("不支持的文件类型，仅支持 pdf/docx/txt/md")

        file_size = len(content)
        if file_size > MAX_FILE_SIZE:
            raise ValueError(f"文件过大（{file_size // 1024}KB），限制 10MB")
        if file_size == 0:
            raise ValueError("上传的是空文件")

        ext = get_extension(filename)
        stored_name = f"{uuid.uuid4().hex}.{ext}"
        storage_path = UPLOAD_DIR / stored_name
        storage_path.write_bytes(content)

        # 1. 保存文件记录
        file_record = FileRecord(
            user_id=user_id, filename=filename, stored_name=stored_name,
            file_type=ext, file_size=file_size, storage_path=str(storage_path),
            status="uploaded",
        )
        db.add(file_record)
        db.commit()
        db.refresh(file_record)

        # 2. 解析
        try:
            text = parse_file(str(storage_path), ext)
            file_record.parsed_text = text
            file_record.status = "parsed"
            db.commit()
            db.refresh(file_record)
        except Exception as e:
            file_record.status = "failed"
            db.commit()
            raise ValueError(f"文件解析失败: {str(e)}")

        # 3. 自动索引到知识库（如果用户配了 Embedding Key）
        rag_indexed = False
        rag_error = None
        try:
            user_cfg = db.query(UserConfig).filter(UserConfig.user_id == user_id).first()
            if user_cfg and user_cfg.embedding_api_key:
                from app.services.rag_service import rag_service
                await rag_service.index_document(db, user_id, filename, content)
                rag_indexed = True
                logger.info("已自动索引到知识库：%s", filename)
        except Exception as e:
            rag_error = str(e)
            logger.warning("自动索引失败：%s", e)

        # 4. 创建 task 记录
        task = Task(
            user_id=user_id,
            task_type="file_summary",
            input_text=f"文件：《{filename}》",
            status="processing",
        )
        db.add(task)
        db.commit()
        db.refresh(task)

        # 5. AI 处理
        try:
            prompt = f"以下是用户上传的文件《{filename}》的内容，请帮我总结要点：\n\n{text[:6000]}"
            ai_result = await ai_router.handle(db, user_id, prompt)

            task.task_type = ai_result["task_type"]
            task.output_text = ai_result["output"]
            task.status = "done"
            db.commit()
            db.refresh(task)
        except Exception as e:
            task.status = "failed"
            task.output_text = f"处理失败: {str(e)}"
            db.commit()
            raise

        # 6. 在 AI 输出末尾加索引提示
        output = ai_result["output"]
        if rag_indexed:
            output += f"\n\n---\n📚 已自动加入知识库，你可以继续问我关于《{filename}》的任何问题"
        elif rag_error:
            output += f"\n\n---\n⚠️ 未加入知识库（{rag_error[:50]}）"

        return {
            "file": file_record,
            "task_type": ai_result["task_type"],
            "ai_output": output,
            "rag_indexed": rag_indexed,
        }


file_service = FileService()