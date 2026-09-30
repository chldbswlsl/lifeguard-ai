from typing import Literal

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

DEV_SECRET_KEY = "dev-only-secret-key-change-me-in-production"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    app_env: Literal["development", "test", "production"] = "development"
    database_url: str = "postgresql+psycopg://lifeguard:lifeguard@localhost:5432/lifeguard"
    secret_key: str = DEV_SECRET_KEY
    access_token_expire_minutes: int = 60 * 24
    cors_origins: list[str] = ["http://localhost:5173"]
    # nginx 같은 리버스 프록시 뒤에서 운영할 때만 True. X-Forwarded-For의 마지막 값을 클라이언트 IP로 쓴다.
    trust_proxy: bool = False
    max_body_bytes: int = 512 * 1024

    # 로그인 실패 제한: 같은 이메일(또는 같은 IP)로 N번 틀리면 M분 잠금
    login_max_failures: int = 5
    login_lock_minutes: int = 15

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    @model_validator(mode="after")
    def _check_production_secrets(self) -> "Settings":
        if self.is_production and (self.secret_key == DEV_SECRET_KEY or len(self.secret_key) < 32):
            raise ValueError(
                "운영 환경(APP_ENV=production)에서는 SECRET_KEY를 32자 이상의 랜덤 문자열로 설정해야 합니다. "
                '예: python -c "import secrets; print(secrets.token_urlsafe(48))"'
            )
        return self


settings = Settings()
