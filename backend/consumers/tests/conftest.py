import pytest
from unittest.mock import Mock

from consumers.config import ConsumerConfig
from consumers.message_handlers import KafkaPayloadHandler


@pytest.fixture
def consumer_config():
    return ConsumerConfig(
        bootstrap_servers='localhost:9092',
        group_id='test-group',
        auto_offset_reset='earliest',
        enable_auto_commit=False,
    )


@pytest.fixture
def auto_commit_config():
    return ConsumerConfig(
        bootstrap_servers='localhost:9092',
        group_id='test-group',
        auto_offset_reset='earliest',
        enable_auto_commit=True,
    )


@pytest.fixture
def mock_handler():
    return Mock(spec=KafkaPayloadHandler)
