# Loyalty Platform API

[![Python](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![Django](https://img.shields.io/badge/Django-5.0-092E20?logo=django&logoColor=white)](https://www.djangoproject.com/)
[![DRF](https://img.shields.io/badge/DRF-3.15-A30000?logo=django&logoColor=white)](https://www.django-rest-framework.org/)
[![Celery](https://img.shields.io/badge/Celery-5.3-37814A?logo=celery&logoColor=white)](https://docs.celeryq.dev/)
[![Redis](https://img.shields.io/badge/Redis-5.0-DC382D?logo=redis&logoColor=white)](https://redis.io/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-4169E1?logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![Docker](https://img.shields.io/badge/Docker-2496ED?logo=docker&logoColor=white)](https://www.docker.com/)
[![Pytest](https://img.shields.io/badge/Pytest-8.0-0A9EDC?logo=pytest&logoColor=white)](https://docs.pytest.org/)

**Loyalty Platform API** is a production-ready, multi-tenant SaaS solution designed for scalability and security. It enables businesses to create custom loyalty programs, track transactions, and manage rewards with bank-grade isolation between tenants.

**Live Demo:** [https://13.61.251.242.nip.io/api/docs/](https://13.61.251.242.nip.io/api/docs/)

---

## Key Highlights

* **High Quality Code:** The project follows strict **TDD (Test Driven Development)** principles, achieving **95% test coverage**.
* **Multi-Tenancy:** Data isolation per organization via Middleware.
* **Security:** Hybrid authentication (JWT + API Keys), Rate Limiting.
* **Modern Stack:** Built on the latest stable versions of Django 5 and Python 3.12.

---

## Tech Stack

| Category | Technology | Details |
|----------|------------|---------|
| **Core Framework** | Django 5.0, DRF 3.15 | `djangorestframework-simplejwt` for Auth |
| **Database** | PostgreSQL 16 | Driver: `psycopg 3` (binary) |
| **Async & Caching**| Redis 5.0, Celery 5.3 | Used for Throttling & Background tasks |
| **Testing** | Pytest 8.0 | `pytest-django`, `factory-boy`, `pytest-cov` |
| **Quality Control**| Ruff 0.3 | Linter & Formatter |
| **Deployment** | AWS EC2, Docker, Nginx | CI/CD via GitHub Actions |

---

## Architecture

The system uses a **Service-Oriented Architecture** approach within a monolithic codebase:

1.  **Middleware Layer:** Handles Tenant context resolution (via API Key or User) and Rate Limiting.
2.  **API Layer:** `drf-spectacular` auto-schema generation, ViewSets with strict serializers.
3.  **Business Logic:** Encapsulated in Services/Managers to keep Views thin.
4.  **Async Workers:** Celery + Redis for processing heavy tasks.

---

## Testing Strategy

Testing is the core of this project.

* **Tools:** `pytest` for running tests, `factory-boy` for generating mock data.
* **CI Pipeline:** Tests run automatically on every Push/PR in an isolated Docker container.

---

## CI/CD Pipeline

The project uses GitHub Actions for continuous integration and deployment.

* **Linting:** Checks code quality with Ruff (PEP8 compliance).
* **Testing:** Runs pytest against a service container (Postgres + Redis) to ensure data integrity.
* **Deploy:**
    * Triggered **only** on `push` to `main` AND after successful tests.
    * Connects to **AWS EC2** via SSH.
    * Pulls the latest code (using `git reset --hard` to ensure consistency).
    * Rebuilds containers and applies migrations.
    * **SSL/TLS:** Automatic certificate renewal via Certbot.

---

##  API Documentation

The API allows two modes of interaction, documented in Swagger:

1.  **For Frontend/Admins:** Authenticate via `POST /api/auth/login/` (JWT Bearer Token).
2.  **For Integrations:** Authenticate via headers `X-API-KEY`.

**API schema:** [https://13.61.251.242.nip.io/api/schema/](https://13.61.251.242.nip.io/api/schema/)

---

##  Getting Started

### Prerequisites
* Docker & Docker Compose

### Run Locally
1.  Clone the repository:
    ```bash
    git clone [https://github.com/Volodymyr262/loyalty-platform.git](https://github.com/Volodymyr262/loyalty-platform.git)
    cd loyalty-platform
    ```

2.  Create `.env` file inside root folder:
    ```bash
    POSTGRES_DB=loyalty_db
    POSTGRES_USER=postgres
    POSTGRES_PASSWORD=postgres
    DATABASE_URL=postgres://postgres:postgres@db:5432/loyalty_db
    ```

3.  Build and run with Docker:
    ```bash
    docker compose up -d --build
    ```

4.  **Apply Migrations** :
    ```bash
    docker compose exec web python manage.py migrate
    ```

5.  Access the API documentation at `http://localhost:8000/api/docs/`