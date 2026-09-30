"""HTTP 공통 처리: 클라이언트 IP, 요청 제한 응답, 보안 헤더, 본문 크기 제한, 에러 응답 형식.

에러 응답은 항상 {"detail": "한국어 메시지"} 형식이다.
입력 검증 실패(422)는 항목별 에러를 함께 준다: {"detail": "...", "errors": [{"field", "message"}]}
"""

import logging

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.config import settings
from app.security import RateLimiter

logger = logging.getLogger("lifeguard")


def client_ip(request: Request) -> str:
    if settings.trust_proxy:
        # 프록시(nginx)가 맨 뒤에 붙인 값만 믿는다. 앞쪽 값은 클라이언트가 위조할 수 있다.
        parts = [p.strip() for p in request.headers.get("x-forwarded-for", "").split(",") if p.strip()]
        if parts:
            return parts[-1]
    return request.client.host if request.client else "-"


def ensure_not_limited(limiter: RateLimiter, *keys: str) -> None:
    if wait := limiter.retry_after(*keys):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"시도가 너무 많습니다. {(wait + 59) // 60}분 후에 다시 시도해 주세요",
            headers={"Retry-After": str(wait)},
        )


# ---------- 입력 검증 에러를 한국어로 ----------
FIELD_LABELS = {
    "email": "이메일",
    "password": "비밀번호",
    "new_password": "새 비밀번호",
    "current_password": "현재 비밀번호",
    "name": "이름",
    "phone": "연락처",
    "birth_year": "출생연도",
    "address": "주소",
    "notes": "메모",
    "memo": "메모",
    "wake_time": "기상 시각",
    "sleep_time": "취침 시각",
    "activity_level": "총 활동량",
    "hourly_activity": "시간대별 활동량",
    "meal_count": "식사 횟수",
    "meal_times": "식사 시각",
    "outing_minutes": "외출 시간",
    "appliance_usage": "생활기기 사용",
    "source": "입력 방식",
    "date": "날짜",
    "start": "시작 날짜",
    "end": "끝 날짜",
}


def _korean_message(err: dict) -> str:
    t = err.get("type", "")
    ctx = err.get("ctx") or {}
    if t == "missing":
        return "필수 항목입니다"
    if t == "string_too_short":
        return "값을 입력해 주세요" if ctx.get("min_length") == 1 else f"{ctx.get('min_length')}자 이상 입력해 주세요"
    if t == "string_too_long":
        return f"{ctx.get('max_length')}자 이하로 입력해 주세요"
    if t == "too_long":
        return f"최대 {ctx.get('max_length')}개까지 입력할 수 있습니다"
    if t in ("greater_than_equal", "greater_than"):
        return f"{ctx.get('ge', ctx.get('gt'))} 이상이어야 합니다"
    if t in ("less_than_equal", "less_than"):
        return f"{ctx.get('le', ctx.get('lt'))} 이하여야 합니다"
    if t in ("int_parsing", "int_type", "int_from_float"):
        return "정수를 입력해 주세요"
    if t.startswith("time"):
        return "시각 형식이 올바르지 않습니다 (예: 08:30)"
    if t.startswith("date"):
        return "날짜 형식이 올바르지 않습니다 (예: 2026-09-30)"
    if t == "string_pattern_mismatch":
        return "형식이 올바르지 않습니다"
    if t == "extra_forbidden":
        return "허용되지 않는 항목입니다"
    if t == "enum":
        return f"다음 중 하나여야 합니다: {ctx.get('expected')}"
    if t == "value_error":
        loc = err.get("loc") or ()
        if loc and loc[-1] == "email":
            return "올바른 이메일 형식이 아닙니다"
        # 직접 작성한 ValueError 메시지 ("Value error, ..." 접두어 제거)
        return str(ctx.get("error") or err.get("msg", "")).removeprefix("Value error, ")
    return "값이 올바르지 않습니다"


def validation_errors(exc: RequestValidationError) -> list[dict]:
    result = []
    for err in exc.errors():
        # loc 예: ("body", "hourly_activity", 3) → field "hourly_activity"
        loc = [str(p) for p in err.get("loc", ()) if p not in ("body", "query", "path")]
        field = next((p for p in loc if not p.isdigit()), "") if loc else ""
        result.append({"field": field, "label": FIELD_LABELS.get(field, field), "message": _korean_message(err)})
    return result


# ---------- 앱에 붙이기 ----------
SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "no-referrer",
    "Cache-Control": "no-store",  # API 응답(개인정보)을 브라우저·프록시가 저장하지 않게
}


def install(app: FastAPI) -> None:
    @app.middleware("http")
    async def _limit_body_and_add_headers(request: Request, call_next):
        length = request.headers.get("content-length")
        if length and length.isdigit() and int(length) > settings.max_body_bytes:
            return JSONResponse(
                status_code=status.HTTP_413_CONTENT_TOO_LARGE, content={"detail": "요청 데이터가 너무 큽니다"}
            )
        response = await call_next(request)
        for k, v in SECURITY_HEADERS.items():
            response.headers.setdefault(k, v)
        if request.headers.get("x-forwarded-proto") == "https" or request.url.scheme == "https":
            response.headers.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
        return response

    @app.exception_handler(RequestValidationError)
    async def _on_validation_error(_: Request, exc: RequestValidationError):
        errors = validation_errors(exc)
        summary = " / ".join(f"{e['label']}: {e['message']}" if e["label"] else e["message"] for e in errors)
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            content={"detail": summary or "입력값을 확인해 주세요", "errors": errors},
        )

    @app.exception_handler(StarletteHTTPException)
    async def _on_http_error(_: Request, exc: StarletteHTTPException):
        detail = exc.detail
        if exc.status_code == 404 and detail == "Not Found":
            detail = "없는 API 경로입니다"
        elif exc.status_code == 405 and detail == "Method Not Allowed":
            detail = "허용되지 않는 요청 방식입니다"
        return JSONResponse(status_code=exc.status_code, content={"detail": detail}, headers=exc.headers)

    @app.exception_handler(Exception)
    async def _on_unexpected_error(request: Request, exc: Exception):
        # 내부 정보(스택, SQL 등)는 응답에 넣지 않고 서버 로그에만 남긴다
        logger.exception("처리되지 않은 오류: %s %s", request.method, request.url.path)
        return JSONResponse(
            status_code=500, content={"detail": "서버 내부 오류가 발생했습니다. 잠시 후 다시 시도해 주세요"}
        )
