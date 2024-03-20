import json
from logging import getLogger
from time import sleep

from google.auth.transport import requests
from google.oauth2 import id_token
from google_auth_oauthlib.flow import InstalledAppFlow

from src.auth.constants import CLIENT_SECRET_FILE_PATH
from src.auth.exceptions import InvalidToken
from src.auth.providers.factory import AuthProviderFactory
from src.auth.schemas import GoogleUserInfo
from src.config import get_settings

logger = getLogger(__name__)
settings = get_settings()

REDIRECT_URI = settings.REDIRECT_URI

MAX_TRIES = 5
SLEEP_TIME = 5


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
            while tries < MAX_TRIES:
                response = func(*args, **kwargs)
                if isinstance(response, InvalidToken):
                    tries += 1
                    logger.warning(
                        f"Invalid token. Trying again in {SLEEP_TIME} seconds..."
                    )
                    sleep(SLEEP_TIME)
                    logger.warning("Trying again...")
                    continue

                logger.info("Token verified successfully")
                return response or InvalidToken()

    return wrapper


class GoogleAuthProviderFactory(AuthProviderFactory):
    def __init__(self, config: dict[str, str]):
        super().__init__(config)

    async def get_user_info(self):
        # Fetch Google credentials
        credentials = await self.get_google_credentials()

        # Extract user information from Google credentials
        user_info = self.verify_google_auth(credentials)

        return user_info

    async def get_google_credentials(self) -> dict[str, str]:
        flow = InstalledAppFlow.from_client_secrets_file(
            CLIENT_SECRET_FILE_PATH,
            scopes=[
                "openid",
                "https://www.googleapis.com/auth/userinfo.profile",
                "https://www.googleapis.com/auth/userinfo.email",
                # "https://www.googleapis.com/auth/drive.readonly",
            ],
            redirect_uri=REDIRECT_URI,
        )
        credentials = flow.fetch_token(code=self.config["code"])

        return credentials

    @verify_google_auth_decorator
    def verify_google_auth(
        self, credentials: dict[str, str]
    ) -> GoogleUserInfo | InvalidToken:
        token = credentials["id_token"]
        google_client_id = self.get_google_client_secret()["web"]["client_id"]

        try:
            # Verify the token using the Google OAuth2 token validation endpoint
            id_info = id_token.verify_token(token, requests.Request(), google_client_id)

            return GoogleUserInfo(
                google_access_token=credentials["access_token"], **id_info
            )
        except ValueError as e:
            logger.error(f"Token validation error:\n{e}")
            return InvalidToken()

    @staticmethod
    def get_google_client_secret() -> dict[str, dict[str, str | list]]:
        secret_file: dict[str, dict[str, str | list]] | None
        # load secret file from path and save to dict
        with open(CLIENT_SECRET_FILE_PATH, "r") as f:
            secret_file = json.loads(f.read())

            if not secret_file:
                raise ValueError("Secret file is empty")

        return secret_file
