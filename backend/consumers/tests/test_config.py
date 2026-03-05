import pytest
from dataclasses import FrozenInstanceError

from consumers.config import ConsumerConfig


class TestConsumerConfig:
    """Unit tests for ConsumerConfig dataclass."""

    def test_explicit_values_stored(self):
        """Test that explicitly passed values are stored correctly."""
        cfg = ConsumerConfig(
            bootstrap_servers='broker:9093',
            group_id='my-group',
            auto_offset_reset='latest',
            enable_auto_commit=True,
            auto_commit_interval_ms=5000,
            session_timeout_ms=30000,
            max_poll_interval_ms=600000,
        )
        assert cfg.bootstrap_servers == 'broker:9093'
        assert cfg.group_id == 'my-group'
        assert cfg.auto_offset_reset == 'latest'
        assert cfg.enable_auto_commit is True
        assert cfg.auto_commit_interval_ms == 5000
        assert cfg.session_timeout_ms == 30000
        assert cfg.max_poll_interval_ms == 600000

    def test_frozen_instance_cannot_be_modified(self):
        """Test that frozen dataclass raises on attribute assignment."""
        cfg = ConsumerConfig(
            bootstrap_servers='localhost:9092',
            group_id='test',
        )
        with pytest.raises(FrozenInstanceError):
            cfg.group_id = 'changed'

    def test_to_kafka_dict_returns_all_keys(self):
        """Test to_kafka_dict returns correct confluent_kafka key names."""
        cfg = ConsumerConfig(
            bootstrap_servers='localhost:9092',
            group_id='test-group',
            auto_offset_reset='earliest',
            enable_auto_commit=False,
        )
        d = cfg.to_kafka_dict()
        expected_keys = {
            'bootstrap.servers',
            'group.id',
            'auto.offset.reset',
            'enable.auto.commit',
            'auto.commit.interval.ms',
            'session.timeout.ms',
            'max.poll.interval.ms',
        }
        assert set(d.keys()) == expected_keys

    def test_to_kafka_dict_values_match_attributes(self):
        """Test to_kafka_dict values mirror the dataclass attributes."""
        cfg = ConsumerConfig(
            bootstrap_servers='broker:9093',
            group_id='my-group',
            auto_offset_reset='latest',
            enable_auto_commit=True,
            auto_commit_interval_ms=2000,
            session_timeout_ms=15000,
            max_poll_interval_ms=500000,
        )
        d = cfg.to_kafka_dict()
        assert d['bootstrap.servers'] == 'broker:9093'
        assert d['group.id'] == 'my-group'
        assert d['auto.offset.reset'] == 'latest'
        assert d['enable.auto.commit'] is True
        assert d['auto.commit.interval.ms'] == 2000
        assert d['session.timeout.ms'] == 15000
        assert d['max.poll.interval.ms'] == 500000

    def test_frozen_rejects_arbitrary_attributes(self):
        """Test that frozen dataclass does not allow new attributes."""
        cfg = ConsumerConfig(
            bootstrap_servers='localhost:9092',
            group_id='test',
        )
        with pytest.raises((FrozenInstanceError, TypeError, AttributeError)):
            cfg.nonexistent_attribute = 'value'
