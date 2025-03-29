from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import RedirectResponse
from sqlalchemy import select, insert, delete, update
from sqlalchemy.ext.asyncio import AsyncSession
from auth.db import User, get_async_session
from urls.models import urls
from urls.schemas import UrlCreate, UrlChange
from auth.users import current_user
from redis_folder.tasks import task_expire_url
from redis_folder.redis_func import save_task_id, get_task_id, delete_redis_keys, universal_key_builder
from celery.result import AsyncResult
from datetime import datetime, timedelta
import zlib
import validators
from fastapi_cache.decorator import cache
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
    """
    Создание новой короткой ссылки с опцией использовать алиас
    """
    orig_url = new_url.model_dump()["orig_url"]

    # Проверка, является ли ссылка валидной (http://...)
    if not validators.url(orig_url):
        raise HTTPException(status_code=400, detail={
            "status": "Bad Request",
            "data": "invalid link",
        })
    
    # Использую алиас, если есть
    if new_url.model_dump()["alias"]:
        short_url = "http://" + new_url.model_dump()["alias"]
    else:
        # Если нет алиаса, то берем хеш от входа
        short_url = "http://" + hex(zlib.crc32(orig_url.encode('utf-8')))[2:]

    # Формируем словарь для записи а бд
    url = {
        "user_id": user.id if user else None,
        "orig_url": orig_url,
        "short_url": short_url,
        "expires_at": datetime.now() + timedelta(minutes=10), 
        "date_of_create": datetime.now(),
        "last_usage": datetime.now(),
        "count_ref": 0
    }
    statement = insert(urls).values(**url)
    try:
        await session.execute(statement)
        await session.commit()

        # Очищаем кэш
        await delete_redis_keys("all_urls")

        # Создаем таску на истечение времени актуальности последнего использования
        task = task_expire_url.apply_async(args=[short_url], countdown=60*5)
        print(task.id, type(task.id))
        await save_task_id(short_url, task.id)


        # Создаем таску по истечению времени жизни ссылки
        task_expire_url.apply_async(args=[short_url], countdown=60*10)
        
    except Exception as e:
        # Если ссылка уже существует
        raise HTTPException(status_code=500, detail={
            "status": "error",
            "data": "url already exists"
        })
    return {"status": "success",
            "short_url": short_url}

@router.get("/{short_code}")
@cache(expire=60, key_builder=universal_key_builder("redirect"))
async def get_orig_url(short_code: str, session: AsyncSession = Depends(get_async_session)):
    """
    Перенаправление по короткой ссылке
    """

    # Извлекаем оригинальную ссылку
    query = select(urls).where(urls.c.short_url == "http://" + short_code)
    result = await session.execute(query)
    await session.commit()
    res_url = result.fetchone()

    # Если не нашли, выкидываем ошибку
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
    await delete_redis_keys("stats")

    # Убиваем задачу по удалении ссылки
    # И создаем новую с новой актуальностью
    task_id = await get_task_id("http://" + short_code)
    if task_id:
        AsyncResult(task_id.decode("utf-8")).revoke(terminate=True)

    new_task = task_expire_url.apply_async(args=["http://" + short_code], countdown=60*5)
    await save_task_id("http://" + short_code, new_task.id)
                
    return RedirectResponse(res_url[2])

@router.delete("/{short_code}")
async def delete_url(
    short_code: str,
    user: User = Depends(current_user),
    session: AsyncSession = Depends(get_async_session)
):
    """
    Удаление ссылки вручную
    """

    # Проверка, что пользователь авторизованный
    if user:
        # Достаем строку с ссылкой на входе, чтобы убедиться,
        # что она существует в бд
        query = select(urls.c.user_id).where(urls.c.short_url == "http://" + short_code)
        result = await session.execute(query)
        try:
            res_user_id = result.scalars().all()[0]
        except Exception:
            raise HTTPException(status_code=400, detail={
            "status": "Bad Request",
            "data": "data not found",
            })
        
        # Проверка, что ссылка принадлежит пользователю,
        # который обращается по запросу
        if res_user_id == user.id:
            query = delete(urls).where(urls.c.short_url == "http://" + short_code)
            await session.execute(query)
            await session.commit()

            # Очищаем кэш
            await delete_redis_keys("stats")
            await delete_redis_keys("redirect")
            await delete_redis_keys("search")
            await delete_redis_keys("all_urls")
            return {
                "status": "success",
                "data": "url has been deleted"
            }
        else:
            # Если пользователь не создавал данную ссылку
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
    """
    В этом хендлере я решил сделать возможность
    менять короткий адрес на alias
    """
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
            # Меняем короткую ссылку на алиас, 
            # либо на другой рандомный хеш
            if not url.model_dump()["alias"]:
                short_url = "http://" + hex(zlib.crc32(str(random.random()).encode('utf-8')))[2:]
            else:
                short_url = "http://" + url.model_dump()["alias"]

            # Обновляем короткую ссылку в базе данных
            url = {
                "short_url": short_url
            }
            statement = update(urls).where(urls.c.short_url == "http://" + short_code).values(**url)
            try:
                await session.execute(statement)
                await session.commit()

                # Очищаем кэш
                await delete_redis_keys("stats")
                await delete_redis_keys("redirect")
                await delete_redis_keys("search")

            except Exception:
                # Если такая ссылка уже существует
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
@cache(expire=60, key_builder=universal_key_builder("stats"))
async def get_stats(short_code: str, session: AsyncSession = Depends(get_async_session)):
    """
    Получение статистики по ссылке
    """

    # Добавил здесь это, чтобы было заметно, производится ли 
    # расчет заново, или подтягиваются данные из хеша
    time.sleep(2)
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

@router.get("/search/")
@cache(expire=60, key_builder=universal_key_builder("search"))
async def search_link(original_url: str, session: AsyncSession = Depends(get_async_session)):
    "Поиск короткой ссылки по оригинальной"
    query = select(urls).where(urls.c.orig_url == "http://" + original_url)
    result = await session.execute(query)
    await session.commit()
    res_url = result.fetchone()
    if not res_url:
        raise HTTPException(status_code=400, detail={
            "status": "Bad Request",
            "data": "data not found",
        })
                
    return {"status": "success",
            "short_url": res_url[3]}

@router.get("/all_user_urls/")
@cache(expire=60, key_builder=universal_key_builder("all_urls"))
async def get_all_user_urls(
    user: User = Depends(current_user),
    session: AsyncSession = Depends(get_async_session)
):
    "Выводит все ссылки, созданные юзером"
    if user:
        query = select(urls.c.orig_url).where(urls.c.user_id == user.id)
        result = await session.execute(query)
        all_urls = result.scalars().all()
        return {"status": "success",
                "data": all_urls}
    else:
        raise HTTPException(status_code=401, detail={
            "status": "error",
            "data": "Unauthorized",
        })