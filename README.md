# IoT-Catalog-Hub


## Short description

IoT Catalog Hub is a microservice catalog of IoT devices that provides telemetry ingestion, trigger rules, and message routing. The platform enables device registration, real-time telemetry collection and storage, definition of business rules that react to events, and routing of messages to consumers such as alerts, automation logic, or archival storage.

https://drive.google.com/file/d/1LE-NLDsWG7-AySHRq68_kEkrvKi0QT9n/view?usp=sharing

## Tech stack

Django as API Gateway and admin UI. Python agents for telemetry ingestion via MQTT or HTTP. Java service for rule evaluation. Scala service for streaming processing and aggregation. PostgreSQL or TimescaleDB for metadata and time-series storage. Kafka or RabbitMQ as the messaging broker. Docker and Docker Compose for local development. CI/CD with GitHub Actions or GitLab CI. Observability via Prometheus and Grafana.

## Setup Instructions

**Prerequisites**
- Docker Desktop (macOS/Windows) or Docker Engine (Linux)
- Docker Compose
- Git

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
   # ===============================
   # Notes
   # ===============================
   # - This file is intended as an example and should be copied to `.env` before use.
   # - Override values in `.env` for local development or Docker deployment as needed.
   # - Keep SECRET_KEY secret in production.
   
   # ===============================
   # Django Settings
   # ===============================
   # Generate a new secret key: python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
   SECRET_KEY=django-insecure-change-this-in-production-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
   
   # For local/dev — True (shows errors). For staging/prod — False.
   DEBUG=True
   ALLOWED_HOSTS=localhost,127.0.0.1,0.0.0.0
   
   # ===============================
   # Database Configuration
   # ===============================
   
   # Database name, user, and password
   DB_NAME=iot_hub_db
   DB_USER=iot_user_db
   DB_PASSWORD=iot_password
   
   # Database host:
   # - For local launch without Docker: use DB_HOST=localhost
   #   (make sure PostgreSQL is installed locally, database and user are created)
   # - For Docker Compose launch: use DB_HOST=db
   DB_HOST=db  # or localhost for local PostgreSQL
   DB_PORT=5432
   
   # ===============================
   # CORS Configuration
   # ===============================
   # Set to True only for development (allows all origins)
   CORS_ALLOW_ALL_ORIGINS=False
   
   # Comma-separated list of allowed origins (used when CORS_ALLOW_ALL_ORIGINS=False)
   CORS_ALLOWED_ORIGINS=http://localhost:3000,http://localhost:5173,http://127.0.0.1:3000
   ```

   **Important:** 
   - Generate a secure `SECRET_KEY` for production. You can generate one using:
     ```bash
     python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
     ```
   - Update database credentials to match your PostgreSQL setup
   - Adjust `CORS_ALLOWED_ORIGINS` to match your frontend application URLs

### 3. Start Services with Docker Compose

Start the application and database development services using Docker Compose:

```bash
docker compose up -d --build
```

This command will:
- Build the Docker images
- Start PostgreSQL database
- Run Django migrations
- Seed database with initial development data
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

### 4. Database Setup

The project uses an automated workflow for database management via the `entrypoint.sh` script. When you run `docker compose up`, the system automatically handles the database readiness, schema updates, and initial data.

> Manual intervention is only required if you change the database schema in your Python code or need to re-run the initial data population.

#### **Automated Workflow (Default)**
Every time the container starts, the following sequence is executed automatically:
1. **Wait for DB:** Ensures PostgreSQL is ready to accept connections.
2. **Apply Migrations:** Syncs the database schema with the current models.
3. **Seed Database:** Runs the `seed_db` command to ensure development data exists.

---

#### **Manual Management**

If you modify `models.py` files or need to trigger database tasks manually, use the following commands:

| Task | Command | When to use |
| :--- | :--- | :--- |
| **Create Migrations** | `docker compose exec web python manage.py makemigrations` | After you change any `models.py` file. |
| **Apply Migrations** | `docker compose exec web python manage.py migrate` | To manually sync the DB schema. |
| **Seed Database** | `docker compose exec web python manage.py seed_db` | To populate the DB with initial data manually. |



---

#### **Initial Data Population (Seed)**
The `seed_db` command is **idempotent** (safe to run multiple times). It populates the database with essential development objects:

* **Default Users & Roles:** Creates a `testuser` (Client role) and an `adminuser` (Admin role) with pre-configured passwords.
* **Sample Devices:** Registers initial IoT devices for testing.
* **Metrics & Bindings:** Sets up device-metric associations (e.g., temperature, humidity, battery level).
* **Initial Rules & Events:** Defines default logic rules and populates sample event data.

To manually refresh or verify the initial state, run:
```bash
docker compose exec web python manage.py seed_db
```

### 5. Access the Application

- **API and Admin UI:** http://localhost:8000
- **Swagger UI (API testing)**: http://localhost:5433
- **Django Admin:** http://localhost:8000/admin

**Optional:** Create a superuser to access the Django admin interface:
```bash
docker compose exec web python manage.py createsuperuser
```

For more details, see [docs/dev-environment.md](./docs/dev-environment.md).

## Project workflow

Develop the MVP as a monolith to validate core flows. Then split into microservices for Auth & API Gateway, Device Registry, Telemetry Ingestor, Rule Engine, Stream Aggregator, Worker and Notification Service. Package services as .deb for controlled deployment, build Docker images that install those packages, and automate the pipeline in CI to push artifacts to an internal APT repository and container registry.

## Deliverables

A working MVP and microservice stack in staging. CI pipelines that build .deb packages and Docker images. An internal APT repository with packaged services. Orchestration demo using a docker:dind container. Device simulation scripts and end-to-end integration tests. Documentation including architecture diagrams and OpenAPI specs.

## Contributing

Follow the repository guidelines for branching, testing and CI. Open a pull request for feature work and include tests and documentation for changes.
Before contributing, review the [API Authentication & Style Guide](./docs/api-guide.md) to ensure consistency in endpoints, authentication, and JSON formatting.

## Grading

Intern work is evaluated according to a measurable rubric. See the full details [here](docs/grading.md).
