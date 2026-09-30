from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import Base, engine
from app.routers import auth, records, seniors


@asynccontextmanager
async def lifespan(_: FastAPI):
    # 개발 초기에는 시작할 때 테이블을 만든다. 스키마가 자주 바뀌기 시작하면 Alembic 마이그레이션으로 전환.
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title="LifeGuard AI API",
    description="AI를 활용한 독거노인 생활 안전 관리 서비스",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(seniors.router)
app.include_router(records.router)


@app.get("/health", tags=["상태"])
def health() -> dict[str, str]:
    return {"status": "ok"}
