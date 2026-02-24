import os

from django.http import HttpResponse
from prometheus_client import (
    CollectorRegistry,
    generate_latest,
    multiprocess,
    CONTENT_TYPE_LATEST,
)


def metrics_view(request):
    """
    Prometheus metrics endpoint with multiprocess support.

    In a multiprocess setup (Django web + Celery workers), each process writes
    its metrics to a shared directory (PROMETHEUS_MULTIPROC_DIR). This view
    aggregates metrics from all processes and exposes them as a single response.

    If PROMETHEUS_MULTIPROC_DIR is not set, falls back to the default registry
    (single-process mode, suitable for local development without Celery).
    """
    if os.environ.get('PROMETHEUS_MULTIPROC_DIR'):
        registry = CollectorRegistry()
        multiprocess.MultiProcessCollector(registry)
    else:
        from prometheus_client import REGISTRY

        registry = REGISTRY

    data = generate_latest(registry)
    return HttpResponse(data, content_type=CONTENT_TYPE_LATEST)
