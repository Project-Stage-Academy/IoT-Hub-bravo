# Observability Dev Stack

## Running the stack
1. Make sure Docker and Docker Compose are installed.
2. Start the stack:
   ```bash
   docker-compose -f docker-compose.dev.yml up -d prometheus grafana
````

3. Verify that the services are running:

   ```bash
   docker-compose ps
   ```
4. Open Grafana in your browser: [http://localhost:3000](http://localhost:3000)

   * Login: `admin / admin`

## Importing a dashboard

* Use the JSON file at `docs/observability/grafana-dashboard.json` (AC6).

## Adding a metric

1. In your code (e.g., a Celery task or Django view), add a Prometheus metric:

   ```python
   from prometheus_client import Counter

   my_metric = Counter('my_metric_total', 'Description')
   my_metric.inc()
   ```
2. Restart the container so that the metric appears in Prometheus.
3. Add a panel in Grafana → Add Panel → Query → select the new metric.

````

---

### **Troubleshooting**

- **Last N log lines (Django/Celery):**
```bash
docker logs web -n 5
docker logs worker -n 5
````

* **Query Prometheus for high-latency requests (e.g., >1s):**

```promql
rate(django_http_requests_latency_seconds_bucket{le="1.0"}[5m])
```

* **Celery queue length (for support tickets):**

```promql
celery_queue_messages{queue="support-tickets"}
```