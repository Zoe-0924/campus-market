import os

from sqlalchemy import create_engine  # type: ignore
from sqlalchemy.orm import declarative_base, sessionmaker  # type: ignore

try:
    from dotenv import load_dotenv  # type: ignore

    load_dotenv()
except Exception:
    # Render 會直接使用環境變數；本機沒有 python-dotenv 時也不影響執行。
    pass


def get_database_url() -> str:
    """取得資料庫連線字串。

    Render 上請設定 DATABASE_URL，系統會使用 PostgreSQL。
    本機沒有設定 DATABASE_URL 時，會退回使用 SQLite，方便課堂開發測試。
    """
    database_url = os.getenv("DATABASE_URL", "sqlite:///./campus_market.db")

    # 某些平台可能給 postgres://，SQLAlchemy 建議使用 postgresql://。
    if database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql://", 1)

    return database_url


SQLALCHEMY_DATABASE_URL = get_database_url()

engine_options = {
    "pool_pre_ping": True,
}

if SQLALCHEMY_DATABASE_URL.startswith("sqlite"):
    engine_options["connect_args"] = {"check_same_thread": False}

engine = create_engine(SQLALCHEMY_DATABASE_URL, **engine_options)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
