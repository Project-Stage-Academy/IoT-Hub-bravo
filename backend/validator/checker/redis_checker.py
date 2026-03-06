from validator.checker.config import RedisConfig
from validator.checker.idempotency_store import RedisIdempotencyStore
from validator.checker.duplicate_checker import DuplicateChecker
from django.conf import settings
from decouple import config

redis_host = settings.REDIS_HOST
redis_port = settings.REDIS_PORT


def build_redis_checker() -> DuplicateChecker:
    redis_config = RedisConfig(host=redis_host, port=redis_port)
    redis_client = redis_config.create_client()

    store = RedisIdempotencyStore(redis_client=redis_client)
    return DuplicateChecker(store=store)
