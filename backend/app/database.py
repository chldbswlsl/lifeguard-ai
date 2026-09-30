from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.config import settings

if settings.database_url.startswith("sqlite"):
    # 테스트·Docker 없는 로컬 실행용. 메모리 DB(sqlite://)도 연결 하나를 공유해야 테이블이 유지된다.
    engine = create_engine(
        settings.database_url, connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
else:
    engine = create_engine(settings.database_url)
SessionLocal = sessionmaker(bind=engine, autoflush=False)


class Base(DeclarativeBase):
    pass


def get_db() -> Generator[Session]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
