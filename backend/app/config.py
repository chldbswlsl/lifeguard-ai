from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    database_url: str = "postgresql+psycopg://lifeguard:lifeguard@localhost:5432/lifeguard"
    secret_key: str = "dev-only-secret-key-change-me-in-production"  # 운영에서는 .env로 반드시 교체
    access_token_expire_minutes: int = 60 * 24
    cors_origins: list[str] = ["http://localhost:5173"]


settings = Settings()
