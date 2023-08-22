import json
from contextlib import asynccontextmanager
from typing import AsyncGenerator

import sentry_sdk
from fastapi import FastAPI, Depends
from fastapi import Request
from fastapi.middleware.cors import CORSMiddleware
from redis import asyncio as aioredis
from starlette.middleware.sessions import SessionMiddleware
from starlette.responses import HTMLResponse

from src import redis
from src.auth.jwt import parse_jwt_user_data
from src.auth.router import router as auth_router
from src.auth.schemas import JWTData
from src.config import app_configs, settings
from src.database import database


@asynccontextmanager
async def lifespan(_application: FastAPI) -> AsyncGenerator:
    # Startup
    pool = aioredis.ConnectionPool.from_url(
        settings.REDIS_URL, max_connections=10, decode_responses=True
    )
    redis.redis_client = aioredis.Redis(connection_pool=pool)
    await database.connect()

    yield

    # Shutdown
    await database.disconnect()
    await redis.redis_client.close()


app = FastAPI(**app_configs, lifespan=lifespan)

SECRET_KEY = "OulLJiqkldb436-X6M11hKvr7wvLyG8TPi5PkLf4"
app.add_middleware(SessionMiddleware, secret_key=SECRET_KEY)


@app.get('/')
async def root(request: Request):
    user = request.session.get('user')
    if user:
        data = json.dumps(user)
        html = (
            f"<pre>{data}</pre>"
            "<a href='/auth/logout'>Logout</a>"
        )
        return HTMLResponse(html)
    return HTMLResponse("<a href='/auth/login'>Login</a>")


@app.get('/protected')
def test2(jwt_data: JWTData = Depends(parse_jwt_user_data)):
    return {'message': 'protected api_app endpoint'}


app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_origin_regex=settings.CORS_ORIGINS_REGEX,
    allow_credentials=True,
    allow_methods=("GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"),
    allow_headers=settings.CORS_HEADERS,
)

if settings.ENVIRONMENT.is_deployed:
    sentry_sdk.init(
        dsn=settings.SENTRY_DSN,
        environment=settings.ENVIRONMENT,
    )


@app.get("/healthcheck", include_in_schema=False)
async def healthcheck() -> dict[str, str]:
    return {"status": "ok"}


app.include_router(auth_router, prefix="/auth", tags=["Auth"])
