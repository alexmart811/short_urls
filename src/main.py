from fastapi import Depends, FastAPI, Request
from fastapi_users import FastAPIUsers
from database import User
from auth.schemas import UserCreate, UserRead
from auth.auth import auth_backend
from auth.manager import get_user_manager
from urls.router import router as url_router
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from redis import asyncio as aioredis
from fastapi_cache import FastAPICache 
from fastapi_cache.backends.redis import RedisBackend 
import uvicorn

@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    redis = aioredis.from_url("redis://localhost")
    FastAPICache.init(RedisBackend(redis), prefix="fastapi-cache")
    # await create_db_and_tables()
    yield

app = FastAPI(lifespan=lifespan)

app.include_router(url_router)

# fastapi_users = FastAPIUsers[User, int](
#     get_user_manager, 
#     [auth_backend]
# )

# app.include_router(
#     fastapi_users.get_auth_router(auth_backend), prefix="/auth/jwt", tags=["auth"]
# )
# app.include_router(
#     fastapi_users.get_register_router(UserRead, UserCreate),
#     prefix="/auth",
#     tags=["auth"],
# )

# current_user = fastapi_users.current_user(active=True)

# @app.get("/protected-route")
# def protected_route(user: User = Depends(current_user)):
#     return f"Hello, {user.username}"

# @app.get("/unprotected-route")
# def unprotected_route():
#     return f"Hello, anonym"


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", log_level="info", reload=True)