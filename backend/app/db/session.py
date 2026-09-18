"""数据库连接管理：负责创建引擎和提供会话。"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

from app.core.config import settings

# 1. 创建数据库引擎
# connect_args={"check_same_thread": False} 是 SQLite 专有参数，为了兼容 FastAPI 多线程
engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in settings.DATABASE_URL else {}
)

# 2. 创建 SessionLocal 类，每个请求都会用它来和数据库对话
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 3. 创建 Base 类，所有数据表模型都要继承它
Base = declarative_base()

# 4. FastAPI 依赖注入：每次请求来，开一个数据库连接，请求完自动关闭
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()