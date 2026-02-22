from dataclasses import dataclass

from decouple import config


@dataclass(frozen=True, slots=True)
class ConsumerConfig:
    bootstrap_servers: str = config('KAFKA_BOOTSTRAP_SERVERS', default='kafka:9092')
    group_id: str = config('KAFKA_GROUP_ID', default='kafka-consumer')
    auto_offset_reset: str = config('KAFKA_AUTO_OFFSET_RESET', default='earliest')
    enable_auto_commit: bool = config('KAFKA_ENABLE_AUTO_COMMIT', default=False, cast=bool)
    auto_commit_interval_ms: int = config('KAFKA_AUTO_COMMIT_INTERVAL_MS', default=1000, cast=bool)
    session_timeout_ms: int = config('KAFKA_SESSION_TIMEOUT_MS', default=10000, cast=int)
    max_poll_interval_ms: int = config('KAFKA_MAX_POLL_INTERVAL_MS', default=300000, cast=int)

    def to_kafka_dict(self) -> dict:
        return {
            'bootstrap.servers': self.bootstrap_servers,
            'group.id': self.group_id,
            'auto.offset.reset': self.auto_offset_reset,
            'enable.auto.commit': self.enable_auto_commit,
            'auto.commit.interval.ms': self.auto_commit_interval_ms,
            'session.timeout.ms': self.session_timeout_ms,
            'max.poll.interval.ms': self.max_poll_interval_ms,
        }
