from celery import Celery
from sqlalchemy import delete
from urls.models import urls
from auth.db import get_async_session
from redis_func import delete_stats_id
import asyncio

app = Celery('tasks', broker='redis://localhost:6379')

@app.task
def task_expire_url(short_url: str):
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

@app.task
def delete_stats_id_task(short_url: str):
    delete_stats_id(short_url)