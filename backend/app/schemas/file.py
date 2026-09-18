"""文件接口的输入输出格式。"""
from datetime import datetime
from pydantic import BaseModel


class FileResponse(BaseModel):
    id: int
    filename: str
    file_type: str
    file_size: int
    status: str
    created_at: datetime

    class Config:
        from_attributes = True


class FileProcessResponse(BaseModel):
    """文件上传 + 自动 AI 处理后的返回格式。"""
    file: FileResponse
    task_type: str       # AI 判断的任务类型
    ai_output: str       # AI 的处理结果