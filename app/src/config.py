from functools import lru_cache
from typing import Any

from pydantic import PostgresDsn, RedisDsn, model_validator
from pydantic_settings import BaseSettings

from src.constants import Environment


class Config(BaseSettings):
    DEBUG: bool = True

    DATABASE_URL: PostgresDsn = PostgresDsn(
        "postgresql://postgres:postgres@localhost:5432/postgres"
    )
    TEST_DATABASE_URL: PostgresDsn = PostgresDsn(
        "postgresql://postgres:postgres@localhost:5432/postgres"
    )
    REDIS_URL: RedisDsn = RedisDsn("redis://localhost:6379/0")

    SITE_DOMAIN: str = "myapp.com"

    MEDIA_DIR: str = "/src/media/"

    ENVIRONMENT: Environment = Environment.PRODUCTION

    SENTRY_DSN: str | None = None

    CORS_ORIGINS: list[str] | None = None
    CORS_ORIGINS_REGEX: str | None = None
    CORS_HEADERS: list[str] | None = None

    APP_VERSION: str = "1"

    # Google OAuth2
    REDIRECT_URI: str = "http://localhost:8000"
    GLOBAL_LISTENER_PATH: str | None = None

    # Celery
    CELERY_BROKER_URL: str | None = None
    CELERY_RESULT_BACKEND: str | None = None

    # Logging
    LOGGING_CONFIG: str | None = "/home/papaya/backend/app/logging_production_file.ini"

    # Cryptography
    FERNET_KEY: str = "fernet_key"

    # Youtube
    YOUTUBE_PROXY_URL: str | None = None

    @classmethod
    @model_validator(mode="before")
    def validate_sentry_non_local(
        cls, data: dict[str | Environment, Any]
    ) -> dict[str, Any]:
        env: Environment | None = data.get("ENVIRONMENT")
        sentry_dsn: str | None = data.get("SENTRY_DSN")

        if env and env.is_deployed and not sentry_dsn:
            raise ValueError("Sentry is not set")

        return data


@lru_cache()
def get_settings():
    return Config()


settings = get_settings()

app_configs: dict[str, Any] = {"title": "App API"}
if settings.ENVIRONMENT.is_deployed:
    app_configs["root_path"] = f"/v{settings.APP_VERSION}"

if not settings.ENVIRONMENT.is_debug:
    app_configs["openapi_url"] = None  # hide docs
