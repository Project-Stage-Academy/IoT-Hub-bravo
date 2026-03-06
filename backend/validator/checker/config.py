from dataclasses import dataclass
import redis


@dataclass
class RedisConfig:
    host: str
    port: int
    db: int = 0

    def create_client(self) -> redis.Redis:
        return redis.Redis(
            host=self.host,
            port=self.port,
            db=self.db,
        )
