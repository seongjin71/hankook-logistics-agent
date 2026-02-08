"""
데이터베이스 엔진 및 세션 관리
- SQLite를 사용한다.
- FastAPI dependency injection용 get_db() 제공.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

from app.config import settings

# SQLite에서는 check_same_thread=False 필요 (FastAPI 멀티스레드 대응)
engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False},
    echo=False,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """FastAPI Depends용 DB 세션 제공."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
