"""通用依赖：从请求头解析 JWT，返回当前用户。"""
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.security import decode_access_token
from app.models.user import User


# 用标准的 HTTP Bearer 方案（Swagger 会显示 🔒 Authorize 按钮）
security = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    db: Session = Depends(get_db),
) -> User:
    """从 Authorization 头解析出当前登录用户。"""

    if credentials is None:
        raise HTTPException(status_code=401, detail="未登录")

    token = credentials.credentials
    user_id = decode_access_token(token)

    if user_id is None:
        raise HTTPException(status_code=401, detail="登录已失效，请重新登录")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=401, detail="用户不存在")

    return user