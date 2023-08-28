from google.auth.transport import requests
from google.oauth2 import id_token
from google_auth_oauthlib.flow import InstalledAppFlow

from src.auth.exceptions import InvalidToken
from src.auth.schemas import GoogleUserInfo
from src.config import get_settings
from src.utils import get_root_path

settings = get_settings()

GOOGLE_CLIENT_ID = settings.GOOGLE_CLIENT_ID
GOOGLE_CLIENT_SECRET = settings.GOOGLE_CLIENT_SECRET
REDIRECT_URI = settings.REDIRECT_URI


async def verify_google_auth(code: str) -> GoogleUserInfo | InvalidToken:
    flow = InstalledAppFlow.from_client_secrets_file(
        rf"{get_root_path()}/auth/client_secret.json",
        scopes=[
            "openid",
            "https://www.googleapis.com/auth/userinfo.profile",
            "https://www.googleapis.com/auth/userinfo.email",
        ],
        redirect_uri=REDIRECT_URI,
    )
    credentials = flow.fetch_token(code=code)

    token = credentials["id_token"]
    try:
        # Verify the token using the Google OAuth2 token validation endpoint
        id_info = id_token.verify_token(token, requests.Request(), GOOGLE_CLIENT_ID)

        return GoogleUserInfo(**id_info)
    except ValueError:
        return InvalidToken()
