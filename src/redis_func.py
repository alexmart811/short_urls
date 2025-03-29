import redis
from typing import Callable

redis_client = redis.StrictRedis(host='localhost', port=6379, db=0)

def save_task_id(short_url, task_id):
    redis_client.set(f"task:{short_url}", task_id)

def get_task_id(short_url):
    return redis_client.get(f"task:{short_url}")

def delete_stats_id(short_url):
    redis_client.delete(f"stats:{short_url}")

def custom_key_builder(
    func: Callable,
    namespace: str = "",
    *args,
    **kwargs
) -> str:
    inner_kwargs = kwargs.get("kwargs", {})
    short_code = inner_kwargs.get("short_code")
    if short_code is None:
        raise ValueError("short_code must be provided")
    short_code = "http://" + short_code
    return f"stats:{short_code}"