from dataclasses import dataclass

from decouple import config


@dataclass(frozen=True, slots=True)
class ProducerConfig:
    bootstrap_servers: str = config("KAFKA_BOOTSTRAP_SERVERS", default="kafka:9092")
    acks: str = "all"
    enable_idempotence: bool = True
    retries: int = 10
    linger_ms: int = 10
    compression_codec: str = "snappy"
    queue_buffering_max_kbytes: int = 10240  # 10MB
    queue_buffering_max_messages: int = 100000

    def to_kafka_dict(self) -> dict:
        return {
            "bootstrap.servers": self.bootstrap_servers,
            "acks": self.acks,
            "enable.idempotence": self.enable_idempotence,
            "retries": self.retries,
            "linger.ms": self.linger_ms,
            "compression.codec": self.compression_codec,
            "queue.buffering.max.kbytes": self.queue_buffering_max_kbytes,
            "queue.buffering.max.messages": self.queue_buffering_max_messages,
        }
