from celery import Celery
from sqlalchemy import delete
from urls.models import urls
from auth.db import get_async_session
import asyncio
from config import REDIS_HOST, REDIS_PORT

app = Celery('tasks', broker=f'redis://{REDIS_HOST}:{REDIS_PORT}')

# Здесь представлен код для исполнения фоновых задач через Celery
@app.task
def task_expire_url(short_url: str):
    """
    Исполнение задачи удаления ссылок по их короткому url
    """
    loop = asyncio.get_event_loop()
    if loop.is_running():
        asyncio.ensure_future(expire_url_async(short_url))
    else:
        loop.run_until_complete(expire_url_async(short_url))

async def expire_url_async(short_url: str):
    async for session in get_async_session():
        try:
            async with session.begin():
                query = delete(urls).where(urls.c.short_url == short_url)
                await session.execute(query)
        finally:
            await session.close()
        break