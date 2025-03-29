from fastapi_cache import FastAPICache 

async def redis_client():
    """
    Получение подключения к редису
    Создал отдельную функцию, тк без нее ругался,
    что нужно создать сначала FastAPICache.init
    (то, что прописано в main.py)
    """
    return FastAPICache.get_backend().redis

async def save_task_id(short_url: str, task_id: str) -> None:
    """
    Создание записи с фоновой таской в редисе
    params:
        short_url: короткая ссылка url
        task_id: номер задачи, которой будет соответствовать ссылка
    """
    redis = await redis_client()
    await redis.set(f"task:{short_url}", task_id)

async def get_task_id(short_url: str) -> str:
    """
    Получение номера задачи по короткой ссылке из редиса
    params:
        short_url: короткая ссылка url
    return:
        Номер задачи
    """
    redis = await redis_client()
    return await redis.get(f"task:{short_url}")

async def delete_redis_keys(namespace: str) -> None:
    """
    Удаляет все ключи Redis, связанные с указанным пространством имен.
    params:
        namespace: название пространства имен
    """
    redis = await redis_client()
    keys = [key async for key in redis.scan_iter(f"fastapi-cache:{namespace}:*")]
    if keys:
        await redis.delete(*keys) 

def universal_key_builder(namespace: str):
    """
    Функция, которая подается в декоратор кешей,
    чтобы можно было складировать в одном хендлере
    несколько кешей в зависимости от входных данных
    params:
        namespace: название пространства имен.
                   Каждому хендлеру соответствует 
                   свое название имен
    """
    def key_builder(func, *args, **kwargs):
        inner_kwargs = kwargs.get("kwargs", {})
        short_code = inner_kwargs.get("short_code")
        return f"fastapi-cache:{namespace}:{short_code}"
    return key_builder