"""HTTP 공통 처리: 보안 헤더, 에러 형식, 본문 크기 제한, 설정 검증."""

import pytest
from fastapi import Request
from pydantic import ValidationError

from app.config import DEV_SECRET_KEY, Settings, settings
from app.http import client_ip
from app.main import app


def test_보안_헤더(client):
    res = client.get("/health")
    assert res.json() == {"status": "ok", "db": "ok"}
    assert res.headers["X-Content-Type-Options"] == "nosniff"
    assert res.headers["X-Frame-Options"] == "DENY"
    assert res.headers["Referrer-Policy"] == "no-referrer"
    assert res.headers["Cache-Control"] == "no-store"
    assert "Strict-Transport-Security" not in res.headers  # http에서는 보내지 않는다
    https = client.get("/health", headers={"X-Forwarded-Proto": "https"})
    assert https.headers["Strict-Transport-Security"].startswith("max-age=")


def test_없는_경로는_한국어_JSON_404(client):
    res = client.get("/no-such-api")
    assert res.status_code == 404
    assert res.json() == {"detail": "없는 API 경로입니다"}
    assert client.put("/health").json() == {"detail": "허용되지 않는 요청 방식입니다"}


def test_너무_큰_요청은_413(client, guardian):
    res = client.post(
        "/seniors",
        content=b"x" * (settings.max_body_bytes + 1),
        headers={**guardian, "Content-Type": "application/json"},
    )
    assert res.status_code == 413
    assert res.json()["detail"] == "요청 데이터가 너무 큽니다"


def test_예상치_못한_오류는_내부정보_없이_500(client):
    @app.get("/_boom")
    def boom():
        raise RuntimeError("secret internal detail")

    from fastapi.testclient import TestClient

    try:
        with TestClient(app, raise_server_exceptions=False) as c:
            res = c.get("/_boom")
        assert res.status_code == 500
        assert "secret" not in res.text
        assert "서버 내부 오류" in res.json()["detail"]
    finally:
        app.router.routes[:] = [r for r in app.router.routes if getattr(r, "path", "") != "/_boom"]


def test_운영환경에서는_기본_비밀키로_시작_불가():
    with pytest.raises(ValidationError, match="SECRET_KEY"):
        Settings(app_env="production", secret_key=DEV_SECRET_KEY)
    with pytest.raises(ValidationError):
        Settings(app_env="production", secret_key="too-short")
    assert Settings(app_env="production", secret_key="x" * 40).is_production


def _request(headers: dict, host: str = "10.0.0.1") -> Request:
    raw = [(k.lower().encode(), v.encode()) for k, v in headers.items()]
    return Request({"type": "http", "headers": raw, "client": (host, 1234)})


def test_클라이언트_IP(monkeypatch):
    req = _request({"X-Forwarded-For": "1.1.1.1, 2.2.2.2"})
    assert client_ip(req) == "10.0.0.1"  # 기본값: 프록시 헤더를 믿지 않는다
    monkeypatch.setattr(settings, "trust_proxy", True)
    assert client_ip(req) == "2.2.2.2"  # 프록시가 붙인 마지막 값만 믿는다
    assert client_ip(_request({})) == "10.0.0.1"


def test_요청제한_키가_너무_많으면_오래된_것부터_삭제():
    from app.security import RateLimiter

    limiter = RateLimiter(limit=1, window_seconds=60, max_keys=3)
    for k in ("a", "b", "c", "d"):
        limiter.hit(k)
    assert limiter.retry_after("a") == 0  # 가장 오래된 키는 밀려났다
    assert limiter.retry_after("d") > 0
