from fastapi import APIRouter
from app.core.config import settings

# 创建一个路由器，类似于一个“子应用”
# 它的作用是管理一组相关的接口，这里就专门管“健康检查”
router = APIRouter()

# @router.get("/health") 是 FastAPI 的装饰器
# 意思是：当有人用 GET 请求访问 /health 这个路径时，执行下面的 health 函数
@router.get("/health")
def health():
    """健康检查：小程序和后端第一次握手用，用来确认后端还活着。"""
    return {
        "status": "ok",      # 固定返回 ok
        "app": settings.APP_NAME,  # 返回应用名字
        "env": settings.APP_ENV,   # 返回当前环境
        "mock": settings.AI_MOCK,  # 返回是否开启了 Mock 模式
    }