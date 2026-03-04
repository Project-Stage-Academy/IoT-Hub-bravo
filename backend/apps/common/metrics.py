"""
Custom Prometheus metrics for IoT Hub ingestion monitoring.

These metrics track:
- Ingestion throughput (messages received/processed)
- Processing latency
- Error rates
- Rule evaluation and event creation

Usage:
    from apps.common.metrics import ingestion_messages_total
    ingestion_messages_total.labels(source='mqtt', status='success').inc()
"""

from prometheus_client import Counter, Histogram, Gauge

# ============================================================
# INGESTION METRICS (MQTT / Kafka)
# ============================================================

ingestion_messages_total = Counter(
    'iot_ingestion_messages_total',
    'Total number of messages received',
    ['source', 'status'],  # source: mqtt/kafka, status: success/error
)

ingestion_latency_seconds = Histogram(
    'iot_ingestion_latency_seconds',
    'Time to process incoming message (seconds)',
    ['source'],
    buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0],
)

ingestion_errors_total = Counter(
    'iot_ingestion_errors_total',
    'Total number of ingestion errors',
    ['source', 'error_type'],  # error_type: parse_error, validation_error, db_error
)

# ============================================================
# RULE PROCESSING METRICS
# ============================================================

rules_evaluated_total = Counter(
    'iot_rules_evaluated_total',
    'Total number of rules evaluated',
    ['rule_type'],  # threshold, rate, composite
)

rules_triggered_total = Counter(
    'iot_rules_triggered_total',
    'Number of rules that triggered (condition matched)',
    ['rule_type'],
)

rule_processing_seconds = Histogram(
    'iot_rule_processing_seconds',
    'Time to process rules for a telemetry point',
    buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0],
)

# ============================================================
# EVENT METRICS
# ============================================================

events_created_total = Counter(
    'iot_events_created_total',
    'Total number of events created',
    ['severity'],  # info, warning, critical
)

events_unacknowledged = Gauge(
    'iot_events_unacknowledged_total', 'Current number of unacknowledged events'
)
