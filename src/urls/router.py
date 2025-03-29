from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import RedirectResponse
from sqlalchemy import select, insert, delete, update
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi_users import FastAPIUsers
from auth.db import User, get_async_session
from urls.models import urls
from urls.schemas import UrlCreate, UrlChange
from auth.schemas import UserCreate, UserRead, UserUpdate
from auth.users import get_user_manager, current_user
from auth.users import auth_backend
from tasks import task_expire_url, delete_stats_id_task
from redis_func import save_task_id, get_task_id, delete_stats_id, custom_key_builder
from celery.result import AsyncResult
from datetime import datetime, timedelta
import zlib
import validators
from fastapi_cache.decorator import cache
from fastapi_cache.coder import JsonCoder
import random
import time

router = APIRouter(
    prefix="/links",
    tags=["Links"]
)

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
    if new_url.model_dump()["alias"]:
        short_url = "http://" + new_url.model_dump()["alias"]
    else:
        short_url = "http://" + hex(zlib.crc32(orig_url.encode('utf-8')))[2:]
    url = {
        "user_id": user.id if user else None,
        "orig_url": orig_url,
        "short_url": short_url,
        "expires_at": datetime.now() + timedelta(minutes=5), 
        "date_of_create": datetime.now(),
        "last_usage": datetime.now(),
        "count_ref": 0

    }
    statement = insert(urls).values(**url)
    try:
        await session.execute(statement)
        await session.commit()

        # Создаем таску на истечение времени актуальности последнего использования
        task = task_expire_url.apply_async(args=[short_url], countdown=60*1)
        save_task_id(short_url, task.id)


        # Создаем таску по истечению времени жизни ссылки
        task_expire_url.apply_async(args=[short_url], countdown=60*2)
        delete_stats_id_task.apply_async(args=[short_url], countdown=60*2)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail={
            "status": "error",
            "data": "url already exists"
        })
    return {"status": "success",
            "short_url": short_url}

@router.get("/{short_code}")
async def get_orig_url(short_code: str, session: AsyncSession = Depends(get_async_session)):
    "Перенаправление по короткой ссылке"
    query = select(urls).where(urls.c.short_url == "http://" + short_code)
    result = await session.execute(query)
    await session.commit()
    res_url = result.fetchone()
    if not res_url:
        raise HTTPException(status_code=400, detail={
            "status": "Bad Request",
            "data": "data not found",
        })
    # Обновляем параметры последнего использования
    url = {
        "last_usage": datetime.now(),
        "count_ref": res_url[7] + 1
    }
    statement = update(urls).where(urls.c.short_url == "http://" + short_code).values(**url)
    await session.execute(statement)
    await session.commit()
    delete_stats_id("http://" + short_code)

    # Убиваем задачу по удалении ссылки
    # И создаем новую с новой актуальностью
    task_id = get_task_id("http://" + short_code)
    if task_id:
        AsyncResult(task_id.decode("utf-8")).revoke(terminate=True)

    new_task = task_expire_url.apply_async(args=["http://" + short_code], countdown=60*1)
    save_task_id("http://" + short_code, new_task.id)
                
    return RedirectResponse(res_url[2])

@router.delete("/{short_code}")
async def delete_url(
    short_code: str,
    user: User = Depends(current_user),
    session: AsyncSession = Depends(get_async_session)
):
    if user:
        query = select(urls.c.user_id).where(urls.c.short_url == "http://" + short_code)
        result = await session.execute(query)
        try:
            res_user_id = result.scalars().all()[0]
        except Exception:
            raise HTTPException(status_code=400, detail={
            "status": "Bad Request",
            "data": "data not found",
            })
        if res_user_id == user.id:
            query = delete(urls).where(urls.c.short_url == "http://" + short_code)
            await session.execute(query)
            await session.commit()
            delete_stats_id("http://" + short_code)
            return {
                "status": "success",
                "data": "url has been deleted"
            }
        else:
            raise HTTPException(status_code=403, detail={
            "status": "error",
            "data": "Forbidden",
            })
    else:
        raise HTTPException(status_code=401, detail={
            "status": "error",
            "data": "Unauthorized",
        })
    
@router.put("/change")
async def change_url(
    url: UrlChange,
    user: User = Depends(current_user),
    session: AsyncSession = Depends(get_async_session)
):
    # В этом хендлере я решил сделать возможность
    # менять короткий адрес на alias
    if user:
        short_code = url.model_dump()["short_code"]
        query = select(urls.c.user_id).where(urls.c.short_url == "http://" + short_code)
        result = await session.execute(query)
        try:
            res_user_id = result.scalars().all()[0]
        except Exception:
            raise HTTPException(status_code=400, detail={
            "status": "Bad Request",
            "data": "data not found",
            })
        if res_user_id == user.id:
            if not url.model_dump()["alias"]:
                short_url = "http://" + hex(zlib.crc32(str(random.random()).encode('utf-8')))[2:]
            else:
                short_url = "http://" + url.model_dump()["alias"]
            url = {
                "short_url": short_url,
                "expires_at": datetime.now() + timedelta(weeks=1), 
                "date_of_create": datetime.now(),
                "last_usage": datetime.now()
            }
            statement = update(urls).where(urls.c.short_url == "http://" + short_code).values(**url)
            try:
                await session.execute(statement)
                await session.commit()
                delete_stats_id("http://" + short_code)
            except Exception:
                raise HTTPException(status_code=500, detail={
                    "status": "error",
                    "data": "url already exists",
                })
            return {
                "status": "success",
                "data": f"new short_url is {short_url}"
            }
        else:
            raise HTTPException(status_code=403, detail={
            "status": "error",
            "data": "Forbidden",
            })
    else:
        raise HTTPException(status_code=401, detail={
            "status": "error",
            "data": "Unauthorized",
        })


@router.get("/{short_code}/stats")
@cache(expire=60, coder=JsonCoder, key_builder=custom_key_builder)
async def get_stats(short_code: str, session: AsyncSession = Depends(get_async_session)):
    time.sleep(5)
    query = select(urls).where(urls.c.short_url == "http://" + short_code)
    result = await session.execute(query)
    await session.commit()
    res_url = result.fetchone()
    if not res_url:
        raise HTTPException(status_code=400, detail={
            "status": "Bad Request",
            "data": "data not found",
        })
    return {
        "status": "success",
        "orig_link": res_url[2],
        "expires_at": res_url[4],
        "date_of_create": res_url[5],
        "last_usage": res_url[6],
        "count_ref": res_url[7]
    }
