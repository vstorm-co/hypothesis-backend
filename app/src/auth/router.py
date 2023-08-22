import os
import random
import string

from authlib.integrations.starlette_client import OAuth
from authlib.integrations.starlette_client import OAuthError
from fastapi import Request
from fastapi import APIRouter, BackgroundTasks, Depends, Response, status
from databases.interfaces import Record
from src.auth.dependencies import (
    valid_refresh_token,
    valid_refresh_token_user,
    valid_user_create,
)
from src.config import settings
from starlette.config import Config
from starlette.responses import JSONResponse, RedirectResponse
from src.auth.jwt import parse_jwt_user_data
from src.auth import jwt, service, utils
from src.auth.schemas import AccessTokenResponse, AuthUser, JWTData, UserResponse

router = APIRouter()

GOOGLE_CLIENT_ID = settings.GOOGLE_CLIENT_ID
GOOGLE_CLIENT_SECRET = settings.GOOGLE_CLIENT_SECRET

# Set up OAuth
config_data = {'GOOGLE_CLIENT_ID': GOOGLE_CLIENT_ID, 'GOOGLE_CLIENT_SECRET': GOOGLE_CLIENT_SECRET}
starlette_config = Config(environ=config_data)
oauth = OAuth(starlette_config)
oauth.register(
    name='google',
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={'scope': 'openid email profile'},
)

# Set up the middleware to read the request session

FRONTEND_URL = 'http://localhost/token'


# @router.route('/login')
# async def login(request: Request):
#     redirect_uri = FRONTEND_URL  # This creates the url for our /auth endpoint
#     return await oauth.google.authorize_redirect(request, redirect_uri)


# @router.route('/token')
# async def auth(request: Request):
#     print(auth_config.JWT_SECRET)
#     try:
#         access_token = await oauth.google.authorize_access_token(request)
#     except OAuthError:
#         raise jwt.CREDENTIALS_EXCEPTION
#     print("Before user_sata")
#     user_data = await oauth.google.parse_id_token(access_token, nonce='')
#     print("After user_data")
#     print(user_data)
#     if service.get_user_by_email(user_data['email']):
#         user = await service.authenticate_user(user_data)
#         return JSONResponse({'result': True, 'access_token': jwt.create_access_token(user=user)})
#     raise jwt.CREDENTIALS_EXCEPTION


@router.route('/login')
async def login(request: Request):
    redirect_uri = FRONTEND_URL  # This creates the url for our /auth endpoint
    return await oauth.google.authorize_redirect(request, redirect_uri)
#
#
# @router.route('/token')
# async def auth(request: Request):
#     print(f"\n\n{request}")
#     access_token = await oauth.google.authorize_access_token(request)
#     user_data = await oauth.google.parse_id_token(request, access_token)
#     if service.get_user_by_email(user_data['email']):
#         return JSONResponse({'result': True, 'access_token': jwt.create_access_token(user_data['email'])})
#
#
# # @router.get('/')
# # def test():
# #     return JSONResponse({'message': 'auth_app'})
#
#


@router.post("/users", status_code=status.HTTP_201_CREATED, response_model=UserResponse)
async def register_user(
        auth_data: AuthUser = Depends(valid_user_create),
) -> dict[str, str]:
    user = await service.create_user(auth_data)
    return {
        "email": user["email"],  # type: ignore
    }


@router.route('/google-auth')
async def google_auth(request: Request):
    try:
        access_token = await oauth.google.authorize_access_token(request)
    except OAuthError:
        raise jwt.CREDENTIALS_EXCEPTION
    # print("Before user_data")
    user_data = await oauth.google.parse_id_token(access_token, nonce='')
    is_user = await service.get_user_by_email(user_data['email'])
    if not is_user:
        characters = string.ascii_letters + string.digits + string.punctuation
        # print("Password: ", password)
        # print("\nUser data! \n\n", user_data)
        user = await service.create_user(user_data)
        return RedirectResponse(url="\\")
        # return JSONResponse({'result': True, 'access_token': jwt.create_access_token(user=user)})
    user = await service.authenticate_user(user_data)
    return JSONResponse({'result': True, 'access_token': jwt.create_access_token(user=user)})
    # print("After user_data")
    # print(user_data)
    # print("Email:", user_data['email'])
    # print(service.get_social_user_by_email(user_data['email']))
    # print("\n\nSERVICE", service.get_social_user_by_email(user_data['email']), "\n\n")
    # is_user = await service.get_social_user_by_email(user_data['email'])
    # print("\n\nUser: \n\n", user)
    # return "K"
    # if is_user:
    #     print("IF")
    #     user = await service.authenticate_social_user(user_data['email'])
    #     print(user)
    #     return JSONResponse({'result': True, 'access_token': jwt.create_access_token(user=user)})
    # user = await service.create_social_user(user_data)
    # return JSONResponse({'result': True, 'access_token': jwt.create_access_token(user=user)})


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
