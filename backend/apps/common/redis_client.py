import redis
from django.conf import settings

_client = None


def get_redis_client() -> redis.Redis:
    """Returns a single Redis client instance"""
    global _client
    if _client is None:
        _client = redis.Redis(**settings.REDIS_CONFIG)
    return _client