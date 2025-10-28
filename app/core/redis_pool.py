# app/core/redis_pool.py
from app.core.redis import make_redis_pool

# Один общий пул на всё приложение
redis_pool = make_redis_pool()
