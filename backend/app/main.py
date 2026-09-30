import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app import http
from app.config import settings
from app.database import Base, SessionLocal, engine
from app.routers import auth, records, seniors

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")


@asynccontextmanager
async def lifespan(_: FastAPI):
    # 개발 초기에는 시작할 때 테이블을 만든다. 스키마가 자주 바뀌기 시작하면 Alembic 마이그레이션으로 전환.
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title="LifeGuard AI API",
    description="AI를 활용한 독거노인 생활 안전 관리 서비스",
    version="0.2.0",
    lifespan=lifespan,
    # 운영 환경에서는 API 문서를 숨긴다
    docs_url=None if settings.is_production else "/docs",
    redoc_url=None,
    openapi_url=None if settings.is_production else "/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=False,  # 토큰은 쿠키가 아니라 Authorization 헤더로 보낸다
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)
http.install(app)

app.include_router(auth.router)
app.include_router(seniors.router)
app.include_router(records.router)


@app.get("/health", tags=["상태"])
def health():
    """서버와 DB 연결 상태."""
    try:
        with SessionLocal() as db:
            db.execute(text("SELECT 1"))
    except Exception:
        http.logger.exception("DB 연결 확인 실패")
        return JSONResponse(status_code=503, content={"status": "error", "db": "unavailable"})
    return {"status": "ok", "db": "ok"}
