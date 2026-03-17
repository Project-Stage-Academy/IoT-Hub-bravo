from abc import ABC, abstractmethod
import redis


class IdempotencyStore(ABC):
    @abstractmethod
    def save_if_not_exists(self, key: str) -> bool:
        """
        Attempt to save the key.
        Returns True if the key was just created,
        False if the key already exists.
        """
        pass


class RedisIdempotencyStore(IdempotencyStore):
    def __init__(self, redis_client: redis.Redis, ttl: int = 3600):
        self._redis = redis_client
        self._ttl = ttl

    def save_if_not_exists(self, key: str) -> bool:
        """
        Atomically set the key in Redis if it does not exist.
        nx=True ensures the key is set only if it does not exist.
        ex=ttl optionally sets the key expiration in seconds.
        Returns True if the key was stored, False otherwise.
        """
        return self._redis.set(key, "1", nx=True, ex=self._ttl) is True
