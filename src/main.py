from fastapi import FastAPI
from urls.router import router as url_router
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from redis import asyncio as aioredis
from fastapi_cache import FastAPICache 
from fastapi_cache.backends.redis import RedisBackend 
from auth.users import auth_backend, fastapi_users
from auth.schemas import UserCreate, UserRead
from config import REDIS_HOST, REDIS_PORT
import uvicorn

@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    redis = await aioredis.from_url(f"redis://{REDIS_HOST}:{REDIS_PORT}")
    FastAPICache.init(RedisBackend(redis), prefix="fastapi-cache")
    # await create_db_and_tables()
    yield

app = FastAPI(lifespan=lifespan)

app.include_router(url_router)

app.include_router(
    fastapi_users.get_auth_router(auth_backend), prefix="/auth/jwt", tags=["auth"]
)

app.include_router(
    fastapi_users.get_register_router(UserRead, UserCreate),
    prefix="/auth",
    tags=["auth"],
)

if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000, log_level="info", reload=True)