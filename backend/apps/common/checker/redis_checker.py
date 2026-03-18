from apps.common.checker.checker_config import RedisConfig
from apps.common.checker.idempotency_store import RedisIdempotencyStore
from apps.common.checker.duplicate_checker import DuplicateChecker
from django.conf import settings
from functools import lru_cache

redis_host = settings.REDIS_HOST
redis_port = settings.REDIS_PORT


@lru_cache(maxsize=1)
def build_redis_checker() -> DuplicateChecker:
    redis_config = RedisConfig(host=redis_host, port=redis_port)
    redis_client = redis_config.create_client()

    store = RedisIdempotencyStore(redis_client=redis_client)
    return DuplicateChecker(store=store)
