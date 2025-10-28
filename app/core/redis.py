# # app/core/redis.py
# import redis.asyncio as redis
# from app.core.settings import settings

# redis_conn = redis.Redis.from_url(settings.REDIS_URL)

from redis.asyncio import from_url, Redis
from app.core.settings import settings

def make_redis_pool() -> Redis:
    return from_url(
        settings.REDIS_URL,
        password=settings.REDIS_PASSWORD or None,
        encoding="utf-8",
        decode_responses=True,
    )
