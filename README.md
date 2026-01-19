# IoT-Catalog-Hub


## Short description

IoT Catalog Hub is a microservice catalog of IoT devices that provides telemetry ingestion, trigger rules, and message routing. The platform enables device registration, real-time telemetry collection and storage, definition of business rules that react to events, and routing of messages to consumers such as alerts, automation logic, or archival storage.

https://drive.google.com/file/d/1LE-NLDsWG7-AySHRq68_kEkrvKi0QT9n/view?usp=sharing

## Tech stack

Django as API Gateway and admin UI. Python agents for telemetry ingestion via MQTT or HTTP. Java service for rule evaluation. Scala service for streaming processing and aggregation. PostgreSQL or TimescaleDB for metadata and time-series storage. Kafka or RabbitMQ as the messaging broker. Docker and Docker Compose for local development. CI/CD with GitHub Actions or GitLab CI. Observability via Prometheus and Grafana.

## Setup Instructions

### 1. Clone the Repository

```bash
git clone <repository-url>
cd IoT-Hub-bravo
```

### 2. Environment Variables Setup

1. Copy the example environment file:
   ```bash
   cp .env.example .env
   ```

2. Edit the `.env` file and configure the following variables:
   ```env
   # Django Settings
   SECRET_KEY=your-secret-key-here-change-in-production
   DEBUG=True
   ALLOWED_HOSTS=localhost,127.0.0.1

   # Database Configuration
   DB_NAME=iot_hub
   DB_USER=postgres
   DB_PASSWORD=your-database-password
   DB_HOST=localhost
   DB_PORT=5432

   # CORS Configuration
   CORS_ALLOW_ALL_ORIGINS=False
   CORS_ALLOWED_ORIGINS=http://localhost:3000,http://localhost:5173
   ```

   **Important:** 
   - Generate a secure `SECRET_KEY` for production. You can generate one using:
     ```bash
     python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
     ```
   - Update database credentials to match your PostgreSQL setup
   - Adjust `CORS_ALLOWED_ORIGINS` to match your frontend application URLs

### 3. Start Services with Docker Compose

Start the application and database services using Docker Compose:

```bash
docker compose up -d --build
```

This command will:
- Build the Docker images
- Start PostgreSQL database
- Start Django application
- Run in detached mode (`-d`)

To view logs:
```bash
docker compose logs -f
```

To stop the services:
```bash
docker compose down
```

### 4. Run Initial Database Migrations

After starting the services, you need to run initial database migrations:

```bash
docker compose exec web python manage.py migrate
```

This will create all necessary database tables for the application.

### 5. Access the Application

- **API and Admin UI:** http://localhost:8000
- **Django Admin:** http://localhost:8000/admin

**Optional:** Create a superuser to access the Django admin interface:
```bash
docker compose exec web python manage.py createsuperuser
```

## Project workflow

Develop the MVP as a monolith to validate core flows. Then split into microservices for Auth & API Gateway, Device Registry, Telemetry Ingestor, Rule Engine, Stream Aggregator, Worker and Notification Service. Package services as .deb for controlled deployment, build Docker images that install those packages, and automate the pipeline in CI to push artifacts to an internal APT repository and container registry.

## Deliverables

A working MVP and microservice stack in staging. CI pipelines that build .deb packages and Docker images. An internal APT repository with packaged services. Orchestration demo using a docker:dind container. Device simulation scripts and end-to-end integration tests. Documentation including architecture diagrams and OpenAPI specs.

## Contributing

Follow the repository guidelines for branching, testing and CI. Open a pull request for feature work and include tests and documentation for changes.

