"""e2e 테스트 준비: 테스트 전용 백엔드(SQLite) + 빌드된 프론트엔드(vite preview)를 띄우고 브라우저를 연다.

실행:  uv run pytest -m e2e
처음 한 번:  uv run playwright install chromium   (프론트엔드는 frontend/ 에서 npm install 되어 있어야 한다)
화면 캡처는 backend/e2e-screenshots/ 에 저장된다 (git 제외).
"""

import os
import shutil
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

import pytest
from playwright.sync_api import Browser, Page, sync_playwright

ROOT = Path(__file__).resolve().parents[3]
BACKEND = ROOT / "backend"
FRONTEND = ROOT / "frontend"
SHOTS = BACKEND / "e2e-screenshots"
API_PORT = int(os.environ.get("E2E_API_PORT", "8765"))
WEB_PORT = int(os.environ.get("E2E_WEB_PORT", "4174"))


def _wait_for(url: str, proc: subprocess.Popen, timeout: float = 60) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if proc.poll() is not None:
            raise RuntimeError(f"{url} 서버가 시작하지 못했습니다 (종료 코드 {proc.returncode})")
        try:
            with urllib.request.urlopen(url, timeout=2):
                return
        except OSError:
            time.sleep(0.3)
    raise TimeoutError(f"{url} 서버가 {timeout}초 안에 뜨지 않았습니다")


def _stop(proc: subprocess.Popen) -> None:
    if proc.poll() is not None:
        return
    if sys.platform == "win32":  # npx는 자식 node 프로세스를 만든다 → 트리째 종료
        subprocess.run(["taskkill", "/PID", str(proc.pid), "/T", "/F"], capture_output=True)
    else:
        proc.terminate()
    proc.wait(timeout=10)


@pytest.fixture(scope="session")
def web_url(tmp_path_factory) -> str:
    npx = shutil.which("npx")
    if npx is None:
        pytest.skip("Node.js(npx)가 없어 e2e 테스트를 건너뜁니다")

    db = tmp_path_factory.mktemp("e2e") / "e2e.db"
    env = {
        **os.environ,
        "DATABASE_URL": f"sqlite:///{db.as_posix()}",
        "APP_ENV": "test",
        "PYTHONIOENCODING": "utf-8",
    }
    subprocess.run([sys.executable, "-m", "app.seed"], cwd=BACKEND, env=env, check=True, capture_output=True)
    subprocess.run([npx, "vite", "build", "--logLevel", "error"], cwd=FRONTEND, check=True)

    api = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app.main:app", "--port", str(API_PORT)],
        cwd=BACKEND,
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    web = subprocess.Popen(
        [npx, "vite", "preview", "--port", str(WEB_PORT), "--strictPort"],
        cwd=FRONTEND,
        env={**os.environ, "API_URL": f"http://127.0.0.1:{API_PORT}"},
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        _wait_for(f"http://127.0.0.1:{API_PORT}/health", api)
        _wait_for(f"http://localhost:{WEB_PORT}/", web)
        yield f"http://localhost:{WEB_PORT}"
    finally:
        _stop(web)
        _stop(api)


@pytest.fixture(scope="session")
def browser() -> Browser:
    with sync_playwright() as p:
        b = p.chromium.launch()
        yield b
        b.close()


@pytest.fixture
def page(browser: Browser, web_url: str, request) -> Page:
    ctx = browser.new_context(base_url=web_url, locale="ko-KR", viewport={"width": 1280, "height": 900})
    pg = ctx.new_page()
    pg.set_default_timeout(10_000)
    errors: list[str] = []
    pg.on("pageerror", lambda e: errors.append(str(e)))
    yield pg
    SHOTS.mkdir(exist_ok=True)
    pg.screenshot(path=SHOTS / f"{request.node.name}.png", full_page=True)
    ctx.close()
    assert not errors, f"브라우저 스크립트 오류: {errors}"


@pytest.fixture(autouse=True)
def _reset_limits_between_tests(web_url):
    # e2e 서버는 별도 프로세스라 요청 제한 카운터를 직접 지울 수 없다.
    # 로그인 실패를 일부러 내는 테스트는 한 번만 실패하므로 한도(5회)에 걸리지 않는다.
    yield
