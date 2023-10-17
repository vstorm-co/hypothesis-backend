from contextlib import asynccontextmanager
from typing import AsyncGenerator

import sentry_sdk
from fastapi import Depends, FastAPI, Header, Request
from fastapi.staticfiles import StaticFiles
from fastapi_pagination import add_pagination
from sqlalchemy.exc import SQLAlchemyError
from starlette.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
from starlette.responses import JSONResponse

from redis import asyncio as aioredis
from src import redis
from src.auth.config import settings as auth_settings
from src.auth.jwt import parse_jwt_user_data
from src.auth.router import router as auth_router
from src.auth.schemas import JWTData
from src.chat.router import router as chat_router
from src.config import app_configs, settings
from src.database import database
from src.organizations.router import router as organization_router
from src.templates.router import router as template_router


@asynccontextmanager
async def lifespan(_application: FastAPI) -> AsyncGenerator:
    # Startup
    pool = aioredis.ConnectionPool.from_url(
        settings.REDIS_URL.unicode_string(), max_connections=10, decode_responses=True
    )
    redis.redis_client = aioredis.Redis(connection_pool=pool)
    await database.connect()

    yield

    # Shutdown
    await database.disconnect()
    await redis.redis_client.close()


app = FastAPI(**app_configs, lifespan=lifespan)

SECRET_KEY = auth_settings.SECRET_KEY
app.add_middleware(SessionMiddleware, secret_key=SECRET_KEY)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_origin_regex=settings.CORS_ORIGINS_REGEX,
    allow_credentials=True,
    allow_methods=("GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"),
    allow_headers=settings.CORS_HEADERS,
)


@app.get("/")
async def root(request: Request):
    return JSONResponse({"message": "Hello World"})


@app.get("/protected")
def test_protected_endpoint(jwt_data: JWTData = Depends(parse_jwt_user_data)):
    return {"message": "protected api_app endpoint"}


@app.get("/healthcheck", include_in_schema=False)
async def healthcheck(db_error: bool = Header(False)) -> dict[str, str]:
    if db_error:
        raise SQLAlchemyError("Mocked database error")
    try:
        await database.connect()
        await database.execute("SELECT 1")
        return {"status": "ok"}
    except SQLAlchemyError as e:
        return {"status": "error", "message": str(e)}


if settings.ENVIRONMENT.is_deployed:
    sentry_sdk.init(
        dsn=settings.SENTRY_DSN,
        environment=settings.ENVIRONMENT,
    )

app.include_router(auth_router, prefix="/auth", tags=["Auth"])
app.include_router(chat_router, prefix="/chat", tags=["Chat"])
app.include_router(organization_router, prefix="/organization", tags=["Organization"])
app.include_router(template_router, prefix="/template", tags=["Template"])
app.mount("/src/media", StaticFiles(directory="media"), name="src/media")
add_pagination(app)
