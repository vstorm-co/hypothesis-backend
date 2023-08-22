from functools import lru_cache
from typing import Any

from pydantic import PostgresDsn, RedisDsn, root_validator
from pydantic_settings import BaseSettings

from src.constants import Environment


class Config(BaseSettings):
    DEBUG: bool = True

    DATABASE_URL: PostgresDsn
    TEST_DATABASE_URL: PostgresDsn
    REDIS_URL: RedisDsn

    SITE_DOMAIN: str = "myapp.com"

    ENVIRONMENT: Environment = Environment.PRODUCTION

    SENTRY_DSN: str | None = None

    CORS_ORIGINS: list[str] | None = None
    CORS_ORIGINS_REGEX: str | None = None
    CORS_HEADERS: list[str] | None = None

    APP_VERSION: str = "1"

    @root_validator(skip_on_failure=True)
    def validate_sentry_non_local(cls, data: dict[str, Any]) -> dict[str, Any]:
        if data["ENVIRONMENT"].is_deployed and not data["SENTRY_DSN"]:
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
