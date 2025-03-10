# Annotation

Welcome to Annotation - an interactive chatbot that aims to provide intelligent responses to your queries and engage in meaningful conversations. 

Our application is designed to be an AI-powered chat assistant that is not only capable of answering your questions but also empathetic enough to provide prompt and relevant responses. Whether you're seeking information, looking for advice, or simply want to have a friendly chat, our chatbot is here to assist you.

In addition to answering questions, we have plans to expand the capabilities of our chatbot. We are currently working on implementing prompts that will enable the chatbot to ask questions of its own, making the interactions even more dynamic and engaging.

Furthermore, we believe that conversations should not be limited to one-on-one interactions. In the future, we plan to introduce the concept of rooms, where multiple users can join in and participate in group discussions facilitated by the chatbot. This will provide a platform for individuals with shared interests to come together, exchange ideas, and foster meaningful connections.

We are continually improving our application and welcome your feedback and suggestions. Join us on this exciting journey as we explore the possibilities of chatbot technology and create an inclusive space for conversations. Enjoy your time interacting with our chatbot, and we hope it enriches your experience!

## Key Features of the Application

- **Production-Ready Components**
    - Gunicorn with dynamic workers configuration (inspired by [@tiangolo](https://github.com/tiangolo))
    - Dockerfile optimized for small size and fast builds, featuring a non-root user
    - JSON logs for improved readability
    - Integration of Sentry for robust error tracking in deployed environments
    
- **Effortless Local Development Setup**
    - Local environment pre-configured with PostgreSQL and Redis for seamless development
    - Convenient script for code linting using tools like `black`, `autoflake`, `isort` (inspired by [@tiangolo](https://github.com/tiangolo))
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

in .env set
```dotenv
GOOGLE_CLIENT_ID=your_client_id
GOOGLE_CLIENT_SECRET=your_client_secret
GOOGLE_REDIRECT_URI=your_redirect_uri
```

The `GOOGLE_REDIRECT_URI` should be the URL of your frontend application's login page.


## ChatGPT API

in .env set
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
