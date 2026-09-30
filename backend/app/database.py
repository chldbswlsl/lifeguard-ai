from collections.abc import Generator

from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.config import settings

if settings.database_url.startswith("sqlite"):
    # 테스트·Docker 없는 로컬 실행용.
    # 메모리 DB(sqlite://)는 연결 하나를 공유해야 테이블이 유지된다 (StaticPool).
    # 파일 DB는 요청마다 연결을 따로 써야 한다. 연결 하나를 여러 스레드가 동시에 쓰면
    # 동시 요청에서 엉뚱한 결과(404/401/500)가 나온다 — 2026-09-30 e2e 테스트에서 발견.
    in_memory = settings.database_url in ("sqlite://", "sqlite:///:memory:")
    engine = create_engine(
        settings.database_url,
        connect_args={"check_same_thread": False},
        **({"poolclass": StaticPool} if in_memory else {}),
    )

    @event.listens_for(engine, "connect")
    def _enable_sqlite_foreign_keys(dbapi_conn, _):
        # SQLite는 기본적으로 외래키(ON DELETE CASCADE)를 무시한다. PostgreSQL과 동작을 맞춘다.
        dbapi_conn.execute("PRAGMA foreign_keys=ON")
else:
    engine = create_engine(settings.database_url, pool_pre_ping=True)

SessionLocal = sessionmaker(bind=engine, autoflush=False)


class Base(DeclarativeBase):
    pass


def get_db() -> Generator[Session]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
