# Athelix API

Athelix API is a FastAPI backend for a fitness and workout tracking platform. The project is structured to support athlete and training data management, including users, profiles, exercises, workout templates, workout sessions, mesocycles, bodyweight logs, and personal records.

The current codebase provides the application foundation: configuration management, database models, Alembic migrations, a Docker-based PostgreSQL environment, seed scripts, and health/database verification endpoints.

## Tech Stack

- FastAPI
- SQLAlchemy 2.x
- PostgreSQL
- Alembic
- Pydantic Settings
- Uvicorn
- Pytest
- Docker Compose
- `uv` for dependency and command management

## Current Features

- FastAPI application bootstrap with environment-based configuration
- PostgreSQL integration using SQLAlchemy and psycopg
- Alembic migration support
- Seed script for exercise data
- Health and database connectivity endpoints
- JWT-based authentication with access and refresh tokens
- Authenticated user profile and bodyweight log endpoints
- Test suite for API, configuration, and database behavior

## Data Model Overview

The project currently models the main entities needed for a training application:

- Users and user profiles
- Exercise catalog with instructions and secondary muscles
- Workout templates and template exercises
- Workout sessions and logged exercise sets
- Mesocycles for structured training blocks
- Bodyweight logs
- Personal records

## API Endpoints

The currently exposed routes are focused on service validation:

- `GET /` - basic welcome response
- `GET /health` - application health status
- `GET /db-test` - simple database connectivity check
- `GET /db-query` - database version/query check
- `POST /auth/register` - create a user account and issue access/refresh tokens
- `POST /auth/login` - authenticate a user and issue access/refresh tokens
- `POST /auth/refresh` - exchange a valid refresh token for a new token pair
- `GET /auth/me` - return the currently authenticated user
- `GET /users/me` - return the current authenticated user
- `PATCH /users/me` - update the current user's username or email
- `GET /users/me/profile` - fetch the current user's profile
- `PUT /users/me/profile` - create or update the current user's profile
- `GET /users/me/body-weight-logs` - list the current user's bodyweight logs
- `POST /users/me/body-weight-logs` - create a new bodyweight log
- `GET /users/me/body-weight-logs/{log_id}` - fetch a specific bodyweight log
- `PATCH /users/me/body-weight-logs/{log_id}` - update a specific bodyweight log
- `DELETE /users/me/body-weight-logs/{log_id}` - delete a specific bodyweight log

Interactive API docs are available at:

- `http://localhost:8000/docs`
- `http://localhost:8000/redoc`

## Project Structure

```text
app/
  api/          API routers and endpoints
  core/         configuration, database, logging
  models/       SQLAlchemy models
  schemas/      Pydantic schemas
alembic/        database migrations
db_init/        PostgreSQL initialization scripts
scripts/        local startup and seed scripts
sql/            SQL seed data
tests/          automated tests
```

## Local Development Setup

### Prerequisites

- Python 3.11+
- `uv`
- Docker and Docker Compose

### 1. Install dependencies

```bash
uv sync
```

### 2. Configure environment variables

Copy `.env.example` to `.env` and update the values for your environment:

```bash
cp .env.example .env
```

Minimum configuration:

```env
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_DB=app_db
POSTGRES_PORT=5432
POSTGRES_CONTAINER_NAME=postgres_db

ADMINER_PORT=8080
ADMINER_CONTAINER_NAME=postgres_adminer

DATABASE_HOST=localhost
DATABASE_PORT=5432
DATABASE_NAME=app_db
DATABASE_USER=postgres
DATABASE_PASSWORD=postgres

DEBUG=True

JWT_SECRET_KEY=replace-with-a-long-random-secret-at-least-32-characters
JWT_REFRESH_SECRET_KEY=replace-with-a-different-long-random-secret
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7
```

### 3. Start the application stack

To start PostgreSQL, run migrations, and launch the API:

```bash
uv run start
```

To reset the database volume, rebuild the local database state, and reseed exercise data:

```bash
uv run start --reset
```

The API will be available at `http://localhost:8000`.

Adminer will be available at `http://localhost:8080`.

## Database Migrations

Apply migrations manually:

```bash
uv run alembic upgrade head
```

Create a new migration:

```bash
uv run alembic revision --autogenerate -m "describe_change"
```

## Running Tests

Run the full test suite:

```bash
uv run pytest
```

Run only fast unit tests:

```bash
uv run pytest -m "not integration"
```

Run integration tests that require PostgreSQL:

```bash
uv run pytest -m integration
```

## Status

This repository is currently at the backend foundation stage. The database schema and application structure are in place, while the public API surface is still minimal and focused on service health and database verification. It is a solid base for expanding into full CRUD and authentication flows.
