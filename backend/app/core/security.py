"""JWT 令牌的生成与验证，以及内部接口通行证的校验。"""
from datetime import datetime, timedelta
import hmac
import secrets

import jwt

from app.core.config import settings


ALGORITHM = "HS256"

# JWT_SECRET 为空时用的占位密钥（仅用于开发环境兜底）
_DEV_FALLBACK_SECRET = "dev-secret-change-in-production"

# 内部通行证：配置留空则进程内随机生成，避免退化成可预测的固定值
_INTERNAL_TOKEN = settings.INTERNAL_TOKEN or secrets.token_urlsafe(32)


def create_access_token(user_id: int) -> str:
    """生成 JWT：把 user_id 编码进去，并设置过期时间。"""
    expire = datetime.utcnow() + timedelta(days=settings.JWT_EXPIRE_DAYS)
    payload = {
        "sub": str(user_id),          # subject = 用户 ID
        "exp": expire,                # 过期时间
        "iat": datetime.utcnow(),     # 签发时间
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=ALGORITHM)


def decode_access_token(token: str) -> int | None:
    """
    解析 JWT，成功返回 user_id，失败返回 None。
    失败情况：签名不对、过期、格式错乱。
    """
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[ALGORITHM])
        return int(payload["sub"])
    except Exception:
        return None


def get_internal_token() -> str:
    """返回当前进程使用的内部通行证。"""
    return _INTERNAL_TOKEN


def verify_internal_token(token: str | None) -> bool:
    """
    校验内部接口通行证，恒定时间比较避免时序侧信道。

    参数:
        token: 请求头里传来的通行证，可能为 None
    返回:
        bool: 校验通过返回 True
    """
    if not token:
        return False
    return hmac.compare_digest(str(token), _INTERNAL_TOKEN)
