import json
from contextlib import asynccontextmanager
from typing import AsyncGenerator

import sentry_sdk
from fastapi import Depends, FastAPI, Header, Request
from sqlalchemy.exc import SQLAlchemyError
from starlette.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
from starlette.responses import HTMLResponse

from redis import asyncio as aioredis
from src import redis
from src.auth.config import settings as auth_settings
from src.auth.jwt import parse_jwt_user_data
from src.auth.router import router as auth_router
from src.auth.schemas import JWTData
from src.config import app_configs, settings
from src.database import database


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
    user = request.session.get("user")
    if user:
        data = json.dumps(user)
        html = f"<pre>{data}</pre>" "<a href='/auth/logout'>Logout</a>"
        return HTMLResponse(html)
    return HTMLResponse("<a href='/auth/login'>Login</a>")


@app.get("/token")
async def token(request: Request):
    return HTMLResponse(
        """
                <button onClick='window.location.href = "/auth/login";'>
                    Login
                </button>
                <br />
                <br />
                <br />
                <script>
                function send(){
                    var req = new XMLHttpRequest();
                    req.onreadystatechange = function() {
                        if (req.readyState === 4) {
                            console.log(req.response);
                            if (req.response["result"] === true) {
                                window.localStorage.setItem(
                                    'jwt', req.response["access_token"]
                                );
                                window.localStorage.setItem(
                                    'refresh', req.response["refresh_token"]
                                );
                            }
                        }
                    }
                    req.withCredentials = true;
                    req.responseType = 'json';
                    req.open("get","/auth/token?"+window.location.search.substr(1),true);
                    req.send("");
                }
                </script>
                <button onClick="send()">Get FastAPI JWT Token</button>

                <button onClick='fetch("http://localhost:8000/healthcheck").then(
                    (r)=>r.json()).then((msg)=>{console.log(msg)});'>
                Call Unprotected API
                </button>
                <button onClick='fetch("http://localhost:8000/protected").then(
                    (r)=>r.json()).then((msg)=>{console.log(msg)});'>
                Call Protected API without JWT
                </button>
                <button onClick='fetch("http://localhost:8000/protected",{
                    headers:{
                        "Authorization": "Bearer " + window.localStorage.getItem("jwt")
                    },
                }).then((r)=>r.json()).then((msg)=>{console.log(msg)});'>
                Call Protected API wit JWT
                </button>

                <button onClick='fetch("http://localhost:8000/auth/logout",{
                    headers:{
                        "Authorization": "Bearer " + window.localStorage.getItem("jwt")
                    },
                }).then((r)=>r.json()).then((msg)=>{
                    console.log(msg);
                    if (msg["result"] === true) {
                        window.localStorage.removeItem("jwt");
                    }
                    });'>
                Logout
                </button>

                <button onClick='fetch("http://localhost:8000/auth/refresh",{
                    method: "POST",
                    headers:{
                        "Authorization": "Bearer " + window.localStorage.getItem("jwt")
                    },
                    body:JSON.stringify({
                        grant_type:\"refresh_token\",
                        refresh_token:window.localStorage.getItem(\"refresh\")
                        })
                }).then((r)=>r.json()).then((msg)=>{
                    console.log(msg);
                    if (msg["result"] === true) {
                        window.localStorage.setItem("jwt", msg["access_token"]);
                    }
                    });'>
                Refresh
                </button>
            """
    )


@app.get("/protected")
def test2(jwt_data: JWTData = Depends(parse_jwt_user_data)):
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
