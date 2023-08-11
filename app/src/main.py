import os

from authlib.integrations.starlette_client import OAuth
from authlib.integrations.starlette_client import OAuthError
from fastapi import FastAPI, Depends
from fastapi import Request
from src import redis
from src.auth.router import router as auth_router
from src.config import app_configs, settings
from src.database import database
from starlette.config import Config
from starlette.middleware.sessions import SessionMiddleware
from starlette.responses import HTMLResponse
from starlette.responses import RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from src.auth.jwt import parse_jwt_user_data
from src.auth.schemas import JWTData

from redis import asyncio as aioredis

# @asynccontextmanager
# async def lifespan(_application: FastAPI) -> AsyncGenerator:
#     # Startup
#     pool = aioredis.ConnectionPool.from_url(
#         settings.REDIS_URL, max_connections=10, decode_responses=True
#     )
#     redis.redis_client = aioredis.Redis(connection_pool=pool)
#     await database.connect()
#
#     yield
#
#     # Shutdown
#     await database.disconnect()
#     await redis.redis_client.close()
#
#
# app = FastAPI(**app_configs, lifespan=lifespan)
app = FastAPI(**app_configs)


@app.on_event("startup")
async def startup_event():
    pool = aioredis.ConnectionPool.from_url(
        settings.REDIS_URL, max_connections=10, decode_responses=True
    )
    redis.redis_client = aioredis.Redis(connection_pool=pool)
    await database.connect()


@app.on_event("shutdown")
async def shutdown_event():
    await database.disconnect()
    await redis.redis_client.close()

SECRET_KEY = "OulLJiqkldb436-X6M11hKvr7wvLyG8TPi5PkLf4"
app.add_middleware(SessionMiddleware, secret_key=SECRET_KEY)


@app.get('/')
async def root():
    return HTMLResponse('<body><a href="/auth/login">Log In</a></body>')


@app.get('/protected')
def test2(jwt_data: JWTData = Depends(parse_jwt_user_data)):
    return {'message': 'protected api_app endpoint'}


@app.get('/token')
async def token(request: Request):
    # print(request)
    return RedirectResponse(url=f'/auth/google-auth?{request.url.query}')
    # return HTMLResponse('''
    #             <script>
    #             function send(){
    #                 var req = new XMLHttpRequest();
    #                 req.onreadystatechange = function() {
    #                     if (req.readyState === 4) {
    #                         console.log(req.response);
    #                         if (req.response["result"] === true) {
    #                             window.localStorage.setItem('jwt', req.response["access_token"]);
    #                         }
    #                     }
    #                 }
    #                 req.withCredentials = true;
    #                 req.responseType = 'json';
    #                 req.open("get", "/auth/google-auth?"+window.location.search.substr(1), true);
    #                 req.send("");
    #
    #             }
    #             </script>
    #             <button onClick="send()">Get FastAPI JWT Token</button>
    #
    #             <button onClick='fetch("http://127.0.0.1:7000/api/").then(
    #                 (r)=>r.json()).then((msg)=>{console.log(msg)});'>
    #             Call Unprotected API
    #             </button>
    #             <button onClick='fetch("https://localhost/protected").then(
    #                 (r)=>r.json()).then((msg)=>{console.log(msg)});'>
    #             Call Protected API without JWT
    #             </button>
    #             <button onClick='fetch("https://localhost/protected",{
    #                 headers:{
    #                     "Authorization": "Bearer " + window.localStorage.getItem("jwt")
    #                 },
    #             }).then((r)=>r.json()).then((msg)=>{console.log(msg)});'>
    #             Call Protected API wit JWT
    #             </button>
    #         ''')

# @app.get('/')
# def public(request: Request):
#     user = request.session.get('user')
#     if user:
#         name = user.get('name')
#         return HTMLResponse(f'<p>Hello {name}!</p><a href=/logout>Logout</a>')
#     return HTMLResponse('<a href=/login>Login</a>')


@app.route('/logout')
async def logout(request: Request):
    request.session.pop('user', None)
    return RedirectResponse(url='/')


# @app.route('/login')
# async def login(request: Request):
#     redirect_uri = request.url_for('auth')  # This creates the url for our /auth endpoint
#     return await oauth.google.authorize_redirect(request, redirect_uri)
#
#
# @app.route('/auth')
# async def auth(request: Request):
#     try:
#         access_token = await oauth.google.authorize_access_token(request)
#     except OAuthError:
#         return RedirectResponse(url='/')
#     # print(access_token)
#     # print(request)
#     # state_data = await app.framework.get_state_data(request)
#     user_data = await oauth.google.parse_id_token(access_token, nonce='')
#     request.session['user'] = dict(user_data)
#     return RedirectResponse(url='/')


app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_origin_regex=settings.CORS_ORIGINS_REGEX,
    allow_credentials=True,
    allow_methods=("GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"),
    allow_headers=settings.CORS_HEADERS,
)
#
# if settings.ENVIRONMENT.is_deployed:
#     sentry_sdk.init(
#         dsn=settings.SENTRY_DSN,
#         environment=settings.ENVIRONMENT,
#     )


@app.get("/healthcheck", include_in_schema=False)
async def healthcheck() -> dict[str, str]:
    return {"status": "ok"}


app.include_router(auth_router, prefix="/auth", tags=["Auth"])
# app.mount('/auth', auth_router)

# from starlette.config import Config
# from authlib.integrations.starlette_client import OAuth
#
# GOOGLE_CLIENT_ID = settings.GOOGLE_CLIENT_ID
# GOOGLE_CLIENT_SECRET = settings.GOOGLE_CLIENT_SECRET
#
# config_data = {'GOOGLE_CLIENT_ID': GOOGLE_CLIENT_ID, 'GOOGLE_CLIENT_SECRET': GOOGLE_CLIENT_SECRET}
# starlette_config = Config(environ=config_data)
# oauth = OAuth(starlette_config)
# oauth.register(
#     name='google',
#     server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
#     client_kwargs={'scope': 'openid email profile'},
# )
#
# from starlette.middleware.sessions import SessionMiddleware
#
# SECRET_KEY = "OulLJiqkldb436-X6M11hKvr7wvLyG8TPi5PkLf4"
# # if SECRET_KEY is None:
# #     raise 'Missing SECRET_KEY'
# app.add_middleware(SessionMiddleware, secret_key=SECRET_KEY)
#
# from fastapi import Request
# from starlette.responses import RedirectResponse
# from authlib.integrations.starlette_client import OAuthError
#
#
# @app.get('/google-login')
# async def google_login(request: Request):
#     redirect_uri = request.url_for('google-auth')
#     return await oauth.google.authorize_redirect(request, redirect_uri)
#
#
# @app.route('/google-auth')
# async def google_auth(request: Request):
#     try:
#         access_token = await oauth.google.authorize_access_token(request)
#     except OAuthError:
#         return RedirectResponse(url='/')
#     user_data = await oauth.google.parse_id_token(request, access_token)
#     request.session['user'] = dict(user_data)
#     return RedirectResponse(url='/')
#
#
# from starlette.responses import HTMLResponse
#
#
# @app.get('/')
# def public(request: Request):
#     user = request.session.get('user')
#     if user:
#         name = user.get('name')
#         return HTMLResponse(f'<p>Hello {name}!</p><a href=/logout>Logout</a>')
#     return HTMLResponse('<a href=/google-login>Login</a>')
