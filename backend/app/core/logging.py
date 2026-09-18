"""日志配置：统一格式与输出，替代散落的 print。"""
import logging
import sys

from fastapi import HTTPException


LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

_configured = False


def setup_logging(debug: bool = False) -> None:
    """
    初始化根 logger。重复调用只生效一次。

    参数:
        debug: 为 True 时日志级别设为 DEBUG，否则 INFO
    返回:
        None
    """
    global _configured
    if _configured:
        return

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter(LOG_FORMAT, datefmt=DATE_FORMAT))

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(logging.DEBUG if debug else logging.INFO)

    # uvicorn 自带 handler，避免同一行日志被打印两次
    for name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        logging.getLogger(name).propagate = False

    _configured = True


def get_logger(name: str) -> logging.Logger:
    """
    获取带统一配置的 logger。

    参数:
        name: 通常传 __name__
    返回:
        logging.Logger
    """
    setup_logging()
    return logging.getLogger(name)


def internal_error(action: str, exc: Exception) -> HTTPException:
    """
    把未预期的异常转成对外通用错误：堆栈写日志，响应里不带任何内部细节。

    参数:
        action: 动作描述，用于拼接对外提示与日志前缀
        exc: 原始异常
    返回:
        HTTPException: 500 状态码，detail 为通用文案
    """
    logging.getLogger("app.error").exception("%s 失败", action)
    return HTTPException(status_code=500, detail=f"{action}失败，请稍后重试")
