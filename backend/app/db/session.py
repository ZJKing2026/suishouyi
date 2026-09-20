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


# 5. 给老库补上后加的列
def ensure_columns():
    """
    补齐已有表缺失的字段。

    SQLite 的 create_all 只建新表，不改已有表结构，新增列要在这里手动补，
    否则老部署升级后启动就会因为缺列报错。
    """
    from sqlalchemy import inspect, text

    inspector = inspect(engine)
    if "user_messages" not in inspector.get_table_names():
        return

    cols = {c["name"] for c in inspector.get_columns("user_messages")}
    if "task_id" not in cols:
        with engine.begin() as conn:
            conn.execute(text("ALTER TABLE user_messages ADD COLUMN task_id INTEGER"))
            conn.execute(text(
                "CREATE INDEX IF NOT EXISTS ix_user_messages_task_id ON user_messages (task_id)"
            ))
        print("🔧 user_messages.task_id 已补齐")