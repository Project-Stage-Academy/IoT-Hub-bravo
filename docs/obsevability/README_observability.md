# Observability Dev Stack

## Running the stack
1. Make sure Docker and Docker Compose are installed.
2. Start the stack:
```bash
   docker compose up -d --build
```

3. Verify that the services are running:

   ```bash
   docker-compose ps
   ```
4. Open Grafana in your browser: [http://localhost:3000](http://localhost:3000)

   * Login: `[GRAFANA_USERNAME] / [GRAFANA_PASSWORD]`

5. Open Prometheus in your browser: [http://localhost:9090](http://localhost:9090)

   * By default, Prometheus usually does not require a login in a local environment.
   * You can check the status of the targets Prometheus is scraping under **Status → Targets**. This shows whether your application is sending metrics.

## Importing a dashboard

* Use the JSON file at `docs/observability/grafana-dashboard-skeleton.json`.

## Adding a metric

1. In your code, add a Prometheus metric:

   ```python
   from prometheus_client import Counter
   ...
   my_metric = Counter('my_metric_total', 'Description')
   ...
   my_metric.inc()
   ```
2. Restart the container so that the metric appears in Prometheus.
3. Add a panel in Grafana → Add Panel → Query → select the new metric.

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

* **Celery queue length:**

```promql
celery_queue_length{queue_name="celery"}
```