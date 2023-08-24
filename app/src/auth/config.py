from functools import lru_cache

from pydantic_settings import BaseSettings


class AuthConfig(BaseSettings):
    JWT_ALG: str = ""
    JWT_SECRET: str = ""
    JWT_EXP: int = 15  # minutes

    REFRESH_TOKEN_KEY: str = "refreshToken"
    REFRESH_TOKEN_EXP: int = 60 * 60 * 24 * 21  # 21 days

    SECURE_COOKIES: bool = True
    SECRET_KEY: str = "secret"


@lru_cache()
def get_settings():
    return AuthConfig()


settings = get_settings()
