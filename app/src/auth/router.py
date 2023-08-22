from authlib.integrations.starlette_client import OAuth
from authlib.integrations.starlette_client import OAuthError
from databases.interfaces import Record
from fastapi import APIRouter, BackgroundTasks, Depends, Response, status, HTTPException
from starlette.config import Config
from starlette.requests import Request
from starlette.responses import RedirectResponse, JSONResponse

from src.auth import jwt, service, utils
from src.auth.dependencies import (
    valid_refresh_token,
    valid_refresh_token_user,
    valid_user_create,
)
from src.auth.jwt import parse_jwt_user_data
from src.auth.schemas import AccessTokenResponse, AuthUser, JWTData, UserResponse
from src.config import settings

router = APIRouter()

GOOGLE_CLIENT_ID = settings.GOOGLE_CLIENT_ID
GOOGLE_CLIENT_SECRET = settings.GOOGLE_CLIENT_SECRET

# Set up OAuth
starlette_config = Config(environ={
    "GOOGLE_CLIENT_ID": GOOGLE_CLIENT_ID,
    "GOOGLE_CLIENT_SECRET": GOOGLE_CLIENT_SECRET
})
oauth = OAuth(starlette_config)
CONF_URL = "https://accounts.google.com/.well-known/openid-configuration"
oauth.register(
    name="google",
    server_metadata_url=CONF_URL,
    client_kwargs={
        "scope": "openid email profile"
    }
)

FRONTEND_URL = "http://localhost/auth/google-token"


@router.route("/login")
async def login(request: Request):
    redirect_uri = FRONTEND_URL
    return await oauth.google.authorize_redirect(request, redirect_uri)


@router.route("/logout")
async def logout(request: Request):
    request.session.pop("user", None)
    return RedirectResponse(url="/")


@router.route("/google-token")
async def google_auth(request: Request):
    try:
        access_token = await oauth.google.authorize_access_token(request)
        request.session["user"] = dict(access_token.get("userinfo"))
    except OAuthError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_data = await oauth.google.parse_id_token(access_token, nonce="")
    user = await service.get_or_create_user(user_data)

    return JSONResponse({
        "result": True,
        "access_token": jwt.create_access_token(user=user)
    })

@router.post("/users", status_code=status.HTTP_201_CREATED, response_model=UserResponse)
async def register_user(
        auth_data: AuthUser = Depends(valid_user_create),
) -> dict[str, str]:
    user = await service.get_or_create_user(auth_data)
    return {
        "email": user["email"],  # type: ignore
    }


@router.get("/users/me", response_model=UserResponse)
async def get_my_account(
    jwt_data: JWTData = Depends(parse_jwt_user_data),
) -> dict[str, str]:
    user = await service.get_user_by_id(jwt_data.user_id)

    return {
        "email": user["email"],  # type: ignore
    }


@router.post("/users/tokens", response_model=AccessTokenResponse)
async def auth_user(auth_data: AuthUser, response: Response) -> AccessTokenResponse:
    user = await service.authenticate_user(auth_data)
    refresh_token_value = await service.create_refresh_token(user_id=user["id"])

    response.set_cookie(**utils.get_refresh_token_settings(refresh_token_value))

    return AccessTokenResponse(
        access_token=jwt.create_access_token(user=user),
        refresh_token=refresh_token_value,
    )


@router.put("/users/tokens", response_model=AccessTokenResponse)
async def refresh_tokens(
    worker: BackgroundTasks,
    response: Response,
    refresh_token: Record = Depends(valid_refresh_token),
    user: Record = Depends(valid_refresh_token_user),
) -> AccessTokenResponse:
    refresh_token_value = await service.create_refresh_token(
        user_id=refresh_token["user_id"]
    )
    response.set_cookie(**utils.get_refresh_token_settings(refresh_token_value))

    worker.add_task(service.expire_refresh_token, refresh_token["uuid"])
    return AccessTokenResponse(
        access_token=jwt.create_access_token(user=user),
        refresh_token=refresh_token_value,
    )


@router.delete("/users/tokens")
async def logout_user(
    response: Response,
    refresh_token: Record = Depends(valid_refresh_token),
) -> None:
    await service.expire_refresh_token(refresh_token["uuid"])

    response.delete_cookie(
        **utils.get_refresh_token_settings(refresh_token["refresh_token"], expired=True)
    )
