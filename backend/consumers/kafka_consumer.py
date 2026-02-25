import json
from typing import Optional, Any
import logging

from confluent_kafka import Consumer, Message, KafkaException

from consumers.config import ConsumerConfig
from consumers.message_handlers import KafkaPayloadHandler

logger = logging.getLogger(__name__)


class KafkaConsumer:
    def __init__(
        self,
        *,
        config: ConsumerConfig,
        topics: list[str],
        handler: KafkaPayloadHandler,
        consume_timeout: float = 1.0,
        decode_json: bool = False,
        consume_batch: bool = False,
        batch_max_size: int = 50,
    ):
        self._consumer = Consumer(config.to_kafka_dict())
        self._consumer.subscribe(topics)
        self._enable_auto_commit = config.enable_auto_commit

        self._handler = handler
        self._consume_timeout = consume_timeout
        self._decode_json = decode_json

        # self._consume - method, called in the consumer loop
        if consume_batch:
            self._consume = self._consume_batch
            self._batch_max_size = batch_max_size
        else:
            self._consume = self._consume_one

        self._running = True

    def start(self) -> None:
        """
        Start the consumer main loop and process messages until shutdown.

        Runs a blocking consumer loop, that fetches messages from Kafka,
        optionally decodes payloads to JSON, forwards them to the configured
        handler, commits offsets if handling succeeds and auto-commit is disabled.

        Graceful shutdown: by calling self.stop() the loop stops, pending work
        in the current iteration is finished, and the consumer is closed.
        """
        try:
            while self._running:
                self._consume()
        except KafkaException:
            logger.exception('Kafka consumer crashed.')
        finally:
            self._consumer.close()
            logger.info('Kafka consumer stopped.')

    def stop(self, *_) -> None:
        """
        Request graceful shutdown of the consumer loop.

        Does not close the Kafka connection immediately. It sets an internal
        flag, so the consumer loop exits after the current iteration completes.

        This method is intended to be called by the application entrypoint.

        Typical usage in an entrypoint module:
            import signal

            consumer = KafkaConsumer(...)

            signal.signal(signal.SIGTERM, consumer.stop)
            signal.signal(signal.SIGINT, consumer.stop)

            consumer.start()
        """
        self._running = False
        logger.info('Shutting down the consumer...')

    def _consume_one(self) -> None:
        """
        Consumes, handles and commits single Kafka message.
        Used in a consumer loop, if consume_batch=False has been provided.
        """
        message = self._consumer.poll(self._consume_timeout)
        if not self._is_valid_message(message):
            return

        payload = self._get_message_payload(message)
        if payload is None:
            logger.error('Skipping commit due to decode failure at %s', message.offset())
            return

        self._handle_and_commit(payload, message)

    def _consume_batch(self) -> None:
        """
        Consumes, handles and commits a batch of Kafka messages.
        Used in a consumer loop, if consume_batch=True has been provided.
        """
        messages = self._consumer.consume(
            num_messages=self._batch_max_size,
            timeout=self._consume_timeout,
        )
        if not messages:
            return

        batch: list[Any] = []
        last_valid_message: Optional[Message] = None

        for message in messages:
            if not self._is_valid_message(message):
                continue

            payload = self._get_message_payload(message)
            if payload is None:
                continue

            if isinstance(payload, list):
                batch.extend(payload)
            else:
                batch.append(payload)

            last_valid_message = message

        if last_valid_message is not None:
            self._handle_and_commit(batch, last_valid_message)

    def _handle_payload(self, payload: Any) -> bool:
        """
        Calls self._handler.handle() method with the provided payload.
        Returns True is no exceptions were raised, and False otherwise.
        """
        try:
            self._handler.handle(payload)
            return True
        except Exception:
            logger.exception('Failed to handle Kafka message payload.')
            return False

    def _handle_and_commit(self, payload: Any, message: Message) -> None:
        """
        Calls self._handle_payload() method with the provided payload.
        If the payload has been handled successfully, and manual
        commitment is required, the message is commited.
        """
        handled_successfully = self._handle_payload(payload)
        if handled_successfully:
            self._commit(message)

    def _commit(self, message: Message) -> None:
        if not self._enable_auto_commit:
            self._consumer.commit(message=message, asynchronous=False)

    @staticmethod
    def _is_valid_message(message: Optional[Message]) -> bool:
        if message is None:
            return False
        if message.error():
            logger.warning('Kafka message error: %s', message.error())
            return False
        return True

    @staticmethod
    def _decode_message(message: Message) -> Optional[Any]:
        raw = message.value()
        if raw is None:
            return None
        try:
            return json.loads(raw.decode('utf-8'))
        except (UnicodeDecodeError, json.JSONDecodeError):
            logger.exception('Failed to decode JSON message.')
            return None

    def _get_message_payload(self, message: Message) -> Optional[Any]:
        if self._decode_json:
            return self._decode_message(message)
        return message.value()
