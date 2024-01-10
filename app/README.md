# Annotation

Welcome to Annotation - an interactive chatbot that aims to provide intelligent responses to your queries and engage in
meaningful conversations.

Our application is designed to be an AI-powered chat assistant that is not only capable of answering your questions but
also empathetic enough to provide prompt and relevant responses. Whether you're seeking information, looking for advice,
or simply want to have a friendly chat, our chatbot is here to assist you.

In addition to answering questions, we have plans to expand the capabilities of our chatbot. We are currently working on
implementing prompts that will enable the chatbot to ask questions of its own, making the interactions even more dynamic
and engaging.

Furthermore, we believe that conversations should not be limited to one-on-one interactions. In the future, we plan to
introduce the concept of rooms, where multiple users can join in and participate in group discussions facilitated by the
chatbot. This will provide a platform for individuals with shared interests to come together, exchange ideas, and foster
meaningful connections.

We are continually improving our application and welcome your feedback and suggestions. Join us on this exciting journey
as we explore the possibilities of chatbot technology and create an inclusive space for conversations. Enjoy your time
interacting with our chatbot, and we hope it enriches your experience!

## Key Features of the Application

- **Production-Ready Components**
    - Gunicorn with dynamic workers configuration (inspired by [@tiangolo](https://github.com/tiangolo))
    - Dockerfile optimized for small size and fast builds, featuring a non-root user
    - JSON logs for improved readability
    - Integration of Sentry for robust error tracking in deployed environments

- **Effortless Local Development Setup**
    - Local environment pre-configured with PostgreSQL and Redis for seamless development
    - Convenient script for code linting using tools like `black`, `autoflake`, `isort` (inspired
      by [@tiangolo](https://github.com/tiangolo))
    - pytest configuration with `async-asgi-testclient`, `pytest-env`, and `pytest-asyncio` for efficient testing
    - Complete type annotations to ensure compliance with `mypy` standards

- **Database Handling with SQLAlchemy and Alembic**
    - Utilization of `asyncpg` for asynchronous database operations
    - Integration of `sqlalchemy2-stubs` for enhanced SQLAlchemy support
    - Organized migrations structured in an easily sortable format (`YYYY-MM-DD_slug`)

- **JWT Authorization Pre-Configured**
    - Implementation of short-lived access tokens for enhanced security
    - Integration of long-lived refresh tokens stored in http-only cookies
    - Secure password storage using `bcrypt` encryption

- **Global Pydantic Model Enhancements**
    - Integration of `orjson` for optimized JSON serialization
    - Explicit timezone configuration during JSON exports

- **Google User Information Retrieval**
    - Capability to obtain and manage information about Google users
    - Seamless integration with Google's authentication and authorization services

- **Additional Enhancements and Utilities**
    - Implementation of global exception handling for better error management
    - Consistent SQLAlchemy key naming convention
    - Practical shortcut scripts for Alembic operations and more

## Google Authentication

### Setup

1. In .env set

```dotenv
GOOGLE_REDIRECT_URI=your_redirect_uri
```

The `GOOGLE_REDIRECT_URI` should be the URL of your frontend application's login page.

2. Download OAuth 2.0 client data from Google console in json format and place it in `app/secrets/` directory.  
   Make sure to name it `client_secret.json`. (Copy of `client_secret.json.example`)

```json
{
  "web": {
    "client_id": "CLIENT_ID",
    "project_id": "PROJECT_ID",
    "auth_uri": "AUTH_URI",
    "token_uri": "TOKEN_URI",
    "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
    "client_secret": "CLIENT_SECRET",
    "redirect_uris": [
      "http://localhost:8000"
    ],
    "javascript_origins": [
      "http://localhost:3000"
    ]
  }
}
```

## ChatGPT API

In .env set

```dotenv
CHATGPT_API_URL=your_chatgpt_api_url
```

## Local Development

### First Build Only

1. `cp .env.example .env`
2. `docker network create traefik_webgateway`
3. Make sure you have `hypothesis_postgres` volume `docker volume create hypothesis_postgres`
3. `docker-compose up -d --build`

### Linters

Format the code

```shell
docker compose exec app format
```

### Migrations

- Create an automatic migration from changes in `src/database.py`

```shell
docker compose exec app makemigrations *migration_name*
```

- Run migrations

```shell
docker compose exec app migrate
```

- Downgrade migrations

```shell
docker compose exec app downgrade -1  # or -2 or base or hash of the migration
```

### Tests

To run tests locally make sure you test db container is up by running
`docker compose -f docker-compose.test.yml up -d`

also keep in mind to check your .env settings for test db

```dotenv
TEST_DB_USER=test_user
TEST_DB_PASSWORD=test_password
TEST_DB_HOST=fastapi-test-db
TEST_DB_NAME=test_app
TEST_DB_PORT=5432
TEST_DATABASE_URL=postgresql://${TEST_DB_USER}:${TEST_DB_PASSWORD}@${TEST_DB_HOST}:${TEST_DB_PORT}/${TEST_DB_NAME}
```

To run your tests type

```shell
docker compose exec app pytest
```

## Database backup

Set backup job with Crontab

```bash
crontab -e

# add the following line, update path if needed
0 1 * * * sh /home/ubuntu/polskiearchiwa.pl/archiwum/etc/backup_database.sh
```

### Restore

1. From backups file copy file with dump, for example

```bash
cp backups/postgres/archiwum_backup_13-07-2023.sql backup.sql
```

2. In `docker-compose.production.yml` uncomment volume with backup.sql file.

```yaml
  - ./backup.sql:/tmp/backup.sql 
```

3. Re-run docker db container

```bash
docker-compose -f docker-compose.production.yml up -d db
# or using available alias
dcupd db 
```

4. Login to db container bash

```bash
docker-compose -f docker-compose.production.yml exec db bash
# or using available alias
dce db bash
```

5. In docker db container login to PostgreSQL database and recreate database

```bash
psql -U postgres 
```

```postgresql
-- create temporary database because we can't drop current used database
CREATE DATABASE temp;
-- enter to temp database
\c temp
-- now we can recreate our database
DROP DATABASE postgres;
CREATE DATABASE postgres;
-- back to bash
\q
```

6. Now we have empty/fresh database, let's import dump file

```bash
psql -U postgres -d postgres < /tmp/backup.sql
```

7. Scroll to check for errors
8. You can exit from docker container

```bash
exit
```

```bash
psql -U postgres -d postgres < /tmp/backup.sql
```

# Celery

In `docker-compose.yml` we have defined services: `celery-beat` and `celery-worker`.
`celery-beat` is responsible for scheduling tasks and `celery-worker` for executing them.

## Celery Beat

Celery Beat is a scheduler; it kicks off tasks at regular intervals.
It does not actually execute the tasks themselves - that is left to the workers.

## Celery Worker

Celery Worker is a program that runs in the background and processes the tasks that are sent to the queue.
It is the workers that actually do the work that your application needs to be done.

## Celery Flower

Celery Flower is a tool for monitoring and administrating Celery clusters.
You can use it to view task progress and details, monitor worker status, and manage and view scheduled tasks.

## How to make celery tasks

In `app.src.tasks` firstly there is a `celery_app` object which is used to register tasks.

```python
from celery import Celery
from src.config import get_settings

settings = get_settings()

celery_app: Celery = Celery(
    "tasks",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=["src.tasks"],
)
```

**make sure you defined `CELERY_BROKER_URL` and `CELERY_RESULT_BACKEND` in your `.env` file.

`app.src.config.py`

```python
# Celery
CELERY_BROKER_URL: str | None = None
CELERY_RESULT_BACKEND: str | None = None
```

Now you can create a celery task in `app.src.tasks` directory.
Example task that is going to be executed every minute:

```python
@celery_app.task
def your_task():
    try:
        logger.info("Running every hour task...")
    except Exception as e:
        logger.error(f"Error in hourly task: {e}")

    return {"status": "OK"}
```

If you want the task to be scheduled you need to add it to `app.src.tasks.celery_app.conf` dictionary.

```python

# Schedule the task to run every minute
celery_app.conf.beat_schedule = {
    "every-minute-task": {
        "task": "src.tasks.your_task",
        "schedule": crontab(hour="*/1"),
    },
}
```

And set extra celery configuration in `celery_app.conf` dictionary.

```python
# Start the Celery Beat scheduler
celery_app.conf.worker_redirect_stdouts = False
celery_app.conf.task_routes = {"tasks.*": {"queue": "celery"}}
celery_app.conf.update(
    result_expires=3600,
)
```

## How to set celery beat and worker scripts to run

In `scripts` directory there are two scripts: `celery-beat.sh` and `celery-worker.sh`.
They are used to run celery beat and worker in docker container.

Configuration of `celery-beat-start.sh`

```bash
#!/bin/bash

set -o errexit
set -o nounset

rm -f './celerybeat.pid'

cd app
celery -A src.tasks.celery_app beat -l info
```

Configuration of `celery-worker-start.sh`

```bash
#!/bin/bash

set -o errexit
set -o nounset

cd app
celery -A src.tasks.celery_app worker --loglevel=info
```

** make sure you passed correct path, in our case it is `src.tasks.celery_app`

## How to check celery beat scheduler

Now you can check the celery beat scheduler in `http://localhost:5555/`
