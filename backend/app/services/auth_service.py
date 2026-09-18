"""登录业务逻辑：code → openid → 用户 → JWT。"""
import httpx
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import create_access_token
from app.models.user import User


class AuthService:
    async def wx_login(
        self,
        db: Session,
        code: str,
        nickname: str | None = None,
        avatar: str | None = None,
    ) -> dict:
        """微信登录：code 换 openid，用户不存在则创建，然后签发 JWT。"""

        # ===== 1. 用 code 换 openid =====
        openid = await self._code_to_openid(code)

        # ===== 2. 查用户 =====
        user = db.query(User).filter(User.openid == openid).first()

        # ===== 3. 不存在则创建 =====
        if not user:
            user = User(
                openid=openid,
                nickname=nickname or f"用户{openid[-6:]}",
                avatar=avatar,
            )
            db.add(user)
            db.commit()
            db.refresh(user)

        # ===== 4. 生成 JWT =====
        token = create_access_token(user.id)

        return {"token": token, "user": user}

    async def _code_to_openid(self, code: str) -> str:
        """用微信 code 换 openid。如果没有配置真实 appid，走 Mock。"""

        # Mock 模式：没配置真实 appid/secret 时，把 code 当 openid 用
        if not settings.WX_APPID or not settings.WX_SECRET:
            return f"mock_openid_{code}"

        # 真实模式：调用微信接口
        url = "https://api.weixin.qq.com/sns/jscode2session"
        params = {
            "appid": settings.WX_APPID,
            "secret": settings.WX_SECRET,
            "js_code": code,
            "grant_type": "authorization_code",
        }
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url, params=params)
            data = resp.json()

        if "openid" not in data:
            raise ValueError(f"微信登录失败: {data}")

        return data["openid"]


auth_service = AuthService()