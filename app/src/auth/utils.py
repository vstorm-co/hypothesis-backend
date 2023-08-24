from typing import Any

import httpx

from src.auth.config import settings as auth_settings
from src.config import get_settings

settings = get_settings()


def get_refresh_token_settings(
    refresh_token: str,
    expired: bool = False,
) -> dict[str, Any]:
    base_cookie = {
        "key": auth_settings.REFRESH_TOKEN_KEY,
        "httponly": True,
        "samesite": "none",
        "secure": auth_settings.SECURE_COOKIES,
        "domain": settings.SITE_DOMAIN,
    }
    if expired:
        return base_cookie

    return {
        **base_cookie,
        "value": refresh_token,
        "max_age": auth_settings.REFRESH_TOKEN_EXP,
    }


def fetch_user_info(access_token: str):
    url = "https://www.googleapis.com/oauth2/v1/userinfo"

    with httpx.Client() as client:
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json",
        }
        params = {"access_token": access_token}
        response = client.get(url, headers=headers, params=params)

        return response.json()
