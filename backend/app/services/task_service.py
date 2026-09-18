"""任务业务逻辑。"""
from sqlalchemy.orm import Session
from app.models.task import Task
from app.ai.router.router import ai_router


class TaskService:
    async def process_task(self, db: Session, user_id: int, content: str) -> Task:
        task = Task(user_id=user_id, input_text=content, status="pending")
        db.add(task)
        db.commit()
        db.refresh(task)

        try:
            task.status = "processing"
            db.commit()

            ai_result = await ai_router.handle(db, user_id, content)   # ← 加 db, user_id

            task.task_type = ai_result["task_type"]
            task.output_text = ai_result["output"]
            task.status = "done"
            db.commit()
            db.refresh(task)
        except Exception as e:
            task.status = "failed"
            task.output_text = f"处理失败: {str(e)}"
            db.commit()
            db.refresh(task)

        return task

    def list_tasks(self, db: Session, user_id: int, limit: int, offset: int):
        query = db.query(Task).filter(Task.user_id == user_id)
        total = query.count()
        tasks = query.order_by(Task.created_at.desc()).offset(offset).limit(limit).all()
        return {"total": total, "items": tasks}


task_service = TaskService()