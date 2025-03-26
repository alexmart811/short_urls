from celery import Celery

app = Celery('tasks', broker='redis://localhost:6379')

@app.task
async def task_expire_url():
    await session.execute(statement)
    await session.commit()
