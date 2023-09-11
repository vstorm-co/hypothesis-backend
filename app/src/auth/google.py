import json
from logging import getLogger
from time import sleep

from google.auth.transport import requests
from google.oauth2 import id_token
from google_auth_oauthlib.flow import InstalledAppFlow

from src.auth.exceptions import InvalidToken
from src.auth.schemas import GoogleUserInfo
from src.config import get_settings
from src.utils import get_root_path

logger = getLogger(__name__)
settings = get_settings()

client_secret_file_path: str = rf"{get_root_path()}/../secrets/client_secret.json"

secret_file: dict[str, dict[str, str | list]] | None
# load secret file from path and save to dict
with open(client_secret_file_path, "r") as f:
    secret_file = json.loads(f.read())

    if not secret_file:
        raise ValueError("Secret file is empty")

# load dict into settings
GOOGLE_CLIENT_ID = secret_file["web"]["client_id"]
# use settings
REDIRECT_URI = settings.REDIRECT_URI


# We were occasionally getting an invalid token error from
# Google's OAuth2 token validation endpoint.
# This decorator will retry the request up to 5 times before giving up.
# This is only enabled in non-production environments.
def verify_google_auth_decorator(func):
    def wrapper(*args, **kwargs):
        if settings.ENVIRONMENT.is_deployed:
            return func(*args, **kwargs)
        else:
            tries = 0
            while tries < 5:
                response = func(*args, **kwargs)
                if isinstance(response, InvalidToken):
                    tries += 1
                    logger.warning("Invalid token. Trying again in 5 seconds...")
                    sleep(5)
                    logger.warning("Trying again...")
                    continue

                logger.info("Token verified successfully")
                return response or InvalidToken()

    return wrapper


async def get_google_credentials(code: str) -> dict[str, str]:
    flow = InstalledAppFlow.from_client_secrets_file(
        client_secret_file_path,
        scopes=[
            "openid",
            "https://www.googleapis.com/auth/userinfo.profile",
            "https://www.googleapis.com/auth/userinfo.email",
        ],
        redirect_uri=REDIRECT_URI,
    )
    credentials = flow.fetch_token(code=code)

    return credentials


@verify_google_auth_decorator
def verify_google_auth(credentials: dict[str, str]) -> GoogleUserInfo | InvalidToken:
    token = credentials["id_token"]

    try:
        # Verify the token using the Google OAuth2 token validation endpoint
        id_info = id_token.verify_token(token, requests.Request(), GOOGLE_CLIENT_ID)

        return GoogleUserInfo(**id_info)
    except ValueError:
        return InvalidToken()
