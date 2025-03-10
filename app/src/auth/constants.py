from src.utils import get_root_path


class ErrorCode:
    AUTHENTICATION_REQUIRED = "Authentication required."
    AUTHORIZATION_FAILED = "Authorization failed. User has no access."
    INVALID_TOKEN = "Invalid token."
    INVALID_CREDENTIALS = "Invalid credentials."
    EMAIL_TAKEN = "Email is already taken."
    REFRESH_TOKEN_NOT_VALID = "Refresh token is not valid."
    REFRESH_TOKEN_REQUIRED = "Refresh token is required either in the body or cookie."
    USER_NOT_FOUND = "User not found."


CLIENT_SECRET_FILE_PATH: str = rf"{get_root_path()}/../secrets/client_secret.json"
