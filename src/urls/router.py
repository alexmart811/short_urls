from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, insert
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi_users import FastAPIUsers
from database import User, get_async_session
from urls.models import urls
from urls.schemas import UrlCreate
from auth.schemas import UserCreate, UserRead, UserUpdate
from auth.manager import get_user_manager
from auth.auth import auth_backend
from datetime import datetime, timedelta
import zlib
import validators
from fastapi_cache.decorator import cache
import time

router = APIRouter(
    prefix="/links",
    tags=["Links"]
)

fastapi_users = FastAPIUsers[User, int](
    get_user_manager, 
    [auth_backend]
)

# router.include_router(
#     fastapi_users.get_auth_router(auth_backend), prefix="/auth/jwt", tags=["auth"]
# )
# router.include_router(
#     fastapi_users.get_register_router(UserRead, UserCreate),
#     prefix="/auth",
#     tags=["auth"],
# )

router.include_router(
    fastapi_users.get_auth_router(auth_backend), prefix="/auth/jwt", tags=["auth"]
)
router.include_router(
    fastapi_users.get_register_router(UserRead, UserCreate),
    prefix="/auth",
    tags=["auth"],
)
router.include_router(
    fastapi_users.get_reset_password_router(),
    prefix="/auth",
    tags=["auth"],
)
router.include_router(
    fastapi_users.get_verify_router(UserRead),
    prefix="/auth",
    tags=["auth"],
)
router.include_router(
    fastapi_users.get_users_router(UserRead, UserUpdate),
    prefix="/users",
    tags=["users"],
)

current_user = fastapi_users.current_user(active=True)

@router.get("/long")
@cache(expire=60)
async def get_long():
    time.sleep(5)
    return "hello"

@router.post("/shorten")
async def create_shorten(
    new_url: UrlCreate,
    user: User = Depends(current_user), 
    session: AsyncSession = Depends(get_async_session)
):
    orig_url = new_url.model_dump()["orig_url"]
    if not validators.url(orig_url):
        raise HTTPException(status_code=400, detail={
            "status": "Bad Request",
            "data": "invalid link",
        })
    short_url = "http://" + hex(zlib.crc32(orig_url.encode('utf-8')))[2:]
    url = {
        "user_id": user.id,
        "orig_url": orig_url,
        "short_url": short_url,
        "expires_at": datetime.now() + timedelta(weeks=1), 
        "date_of_create": datetime.now(),
        "last_usage": datetime.now(),
        "count_ref": 0

    }
    statement = insert(urls).values(**url)
    try:
        await session.execute(statement)
        await session.commit()
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail={
            "status": "error",
            "data": None,
        })

@router.get("/{short_code}")
async def get_orig_url(short_code: str, session: AsyncSession = Depends(get_async_session)):
    query = select(urls.c.orig_url).where(urls.c.short_url == "http://" + short_code)
    result = await session.execute(query)
    res_url = result.scalars().all()
    if not res_url:
        raise HTTPException(status_code=400, detail={
            "status": "Bad Request",
            "data": "data not found",
        })
    return {
        "status": "success",
        "data": res_url
    }