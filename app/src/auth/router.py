from databases.interfaces import Record
from fastapi import APIRouter, BackgroundTasks, Depends, Response, status

from src.auth import jwt, service, utils
from src.auth.dependencies import (
    valid_refresh_token,
    valid_refresh_token_by_user,
    valid_user_create,
)
from src.auth.exceptions import RefreshTokenNotValid
from src.auth.jwt import parse_jwt_user_data
from src.auth.providers.google import GoogleAuthProviderFactory
from src.auth.schemas import (
    AccessTokenResponse,
    AuthUser,
    JWTData,
    RefreshGoogleTokenResponse,
    UserDB,
    UserResponse,
    VerifyResponse,
)
from src.auth.service import get_user_by_id, update_user_google_token

router = APIRouter()


@router.get("/verify", response_model=VerifyResponse)
async def verify_google_code(code: str):
    google_factory = GoogleAuthProviderFactory(
        config={
            "code": code,
        }
    )

    return await google_factory.handle_login()


@router.post("/users", status_code=status.HTTP_201_CREATED, response_model=UserResponse)
async def register_user(
    auth_data: AuthUser = Depends(valid_user_create),
) -> dict[str, str]:
    user = await service.get_or_create_user(auth_data.model_dump())
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
    user: Record = Depends(valid_refresh_token_by_user),
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


@router.put("/refresh-google-token")
async def refresh_google_token(
    refresh_token: str,
    jwt_data: JWTData = Depends(parse_jwt_user_data),
) -> RefreshGoogleTokenResponse:
    access_token = await GoogleAuthProviderFactory(config={}).refresh_access_token(
        refresh_token
    )
    user: Record | None = await get_user_by_id(jwt_data.user_id)
    if not user:
        raise RefreshTokenNotValid()
    user_db = UserDB(**dict(user))
    await update_user_google_token(user_db, access_token)

    if not access_token:
        raise RefreshTokenNotValid()
    return RefreshGoogleTokenResponse(
        google_access_token=access_token,
    )
