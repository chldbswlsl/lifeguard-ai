import datetime as dt
import threading
import time
from collections import OrderedDict, deque

import jwt
from pwdlib import PasswordHash

from app.config import settings

ALGORITHM = "HS256"
_password_hash = PasswordHash.recommended()
# 없는 이메일로 로그인할 때도 해시 검증을 한 번 수행해서, 응답 시간으로 가입 여부를 알아낼 수 없게 한다.
_DUMMY_HASH = _password_hash.hash("dummy-password-for-timing")


def hash_password(password: str) -> str:
    return _password_hash.hash(password)


def verify_password(password: str, hashed: str | None) -> bool:
    if hashed is None:
        _password_hash.verify(password, _DUMMY_HASH)
        return False
    return _password_hash.verify(password, hashed)


def create_access_token(user_id: int, token_version: int) -> str:
    now = dt.datetime.now(dt.UTC)
    payload = {
        "sub": str(user_id),
        "ver": token_version,  # 비밀번호를 바꾸면 버전이 올라가서 이전 토큰이 무효가 된다
        "iat": now,
        "exp": now + dt.timedelta(minutes=settings.access_token_expire_minutes),
    }
    return jwt.encode(payload, settings.secret_key, algorithm=ALGORITHM)


def decode_access_token(token: str) -> tuple[int, int] | None:
    """(user_id, token_version). 잘못되었거나 만료된 토큰이면 None."""
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[ALGORITHM], options={"require": ["sub", "exp"]})
        return int(payload["sub"]), int(payload.get("ver", 0))
    except (jwt.InvalidTokenError, KeyError, ValueError, TypeError):
        return None


class RateLimiter:
    """슬라이딩 윈도 방식의 시도 횟수 제한 (메모리 기반).

    같은 키(이메일, IP, 사용자 ID 등)로 window 안에 limit번 기록되면 잠근다.
    - 서버 프로세스가 하나일 때만 정확하다. 여러 대로 늘리면 Redis 등으로 옮겨야 한다.
    - 키가 max_keys개를 넘으면 가장 오래된 키부터 지운다. 전체를 비우지 않는 이유는,
      공격자가 키를 대량으로 만들어서 다른 키의 카운터를 초기화시키는 것을 막기 위해서다 (bp-portal 방식).
    """

    def __init__(self, limit: int, window_seconds: int, max_keys: int = 5000):
        self.limit = limit
        self.window = window_seconds
        self.max_keys = max_keys
        self._hits: OrderedDict[str, deque[float]] = OrderedDict()
        self._lock = threading.Lock()

    def _prune(self, key: str, now: float) -> deque[float] | None:
        q = self._hits.get(key)
        if q is None:
            return None
        while q and now - q[0] > self.window:
            q.popleft()
        if not q:
            del self._hits[key]
            return None
        return q

    def retry_after(self, *keys: str) -> int:
        """잠겨 있으면 남은 초, 아니면 0."""
        now = time.monotonic()
        with self._lock:
            waits = [
                int(self.window - (now - q[0])) + 1
                for q in (self._prune(k, now) for k in keys)
                if q is not None and len(q) >= self.limit
            ]
        return max(waits, default=0)

    def hit(self, *keys: str) -> None:
        now = time.monotonic()
        with self._lock:
            for k in keys:
                q = self._prune(k, now)
                if q is None:
                    q = self._hits[k] = deque()
                q.append(now)
                self._hits.move_to_end(k)
            while len(self._hits) > self.max_keys:
                self._hits.popitem(last=False)

    def reset(self, *keys: str) -> None:
        with self._lock:
            for k in keys:
                self._hits.pop(k, None)

    def _clear_for_tests(self) -> None:
        with self._lock:
            self._hits.clear()


# 로그인: 실패만 센다. 같은 이메일 또는 같은 IP로 N번 틀리면 M분 잠금
login_limiter = RateLimiter(settings.login_max_failures, settings.login_lock_minutes * 60)
# 회원가입: IP당 1시간에 10번 (CO2 기준과 비슷하게)
signup_limiter = RateLimiter(10, 60 * 60)
# 비밀번호 변경: 사용자당 5분에 10번
password_limiter = RateLimiter(10, 5 * 60)
ALL_LIMITERS = (login_limiter, signup_limiter, password_limiter)
