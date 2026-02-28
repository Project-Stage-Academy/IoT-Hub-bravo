import pytest
from django.db import connection


@pytest.mark.django_db
def test_index_scan_on_device_metric_id():
    query = """
    SELECT * 
    FROM telemetries 
    WHERE device_metric_id = 12
    ORDER BY ts DESC
    LIMIT 10;
    """
    with connection.cursor() as cur:
        cur.execute(f"EXPLAIN {query}")
        plan = "\n".join(row[0] for row in cur.fetchall())

    assert "Index Scan" in plan or "Bitmap Index Scan" in plan


@pytest.mark.django_db
def test_index_scan_on_ts():
    query = """
    SELECT *
    FROM telemetries
    WHERE ts BETWEEN '2026-01-01' AND '2026-01-31'
    ORDER BY ts DESC
    LIMIT 10;
    """
    with connection.cursor() as cur:
        cur.execute(f"EXPLAIN {query}")
        plan = "\n".join(row[0] for row in cur.fetchall())

    assert "Index Scan" in plan or "Bitmap Index Scan" in plan


@pytest.mark.django_db
def test_index_scan_on_device_metric_id_and_ts():
    query = """
    SELECT *
    FROM telemetries
    WHERE device_metric_id = 12
    AND ts BETWEEN '2026-01-01' AND '2026-01-31'
    ORDER BY ts DESC
    LIMIT 10;
    """
    with connection.cursor() as cur:
        cur.execute(f"EXPLAIN {query}")
        plan = "\n".join(row[0] for row in cur.fetchall())

    assert "Index Scan" in plan or "Bitmap Index Scan" in plan


@pytest.mark.django_db
def test_hypertable_scan_without_filters():
    query = """
    SELECT *
    FROM telemetries
    ORDER BY ts DESC
    LIMIT 10;
    """
    with connection.cursor() as cur:
        cur.execute(f"EXPLAIN {query}")
        plan = "\n".join(row[0] for row in cur.fetchall())

    assert "Bitmap Index Scan" in plan or "Index Scan" in plan
