# Athelix API

Athelix API is a FastAPI backend for workout tracking, athlete progress monitoring, mesocycle planning, and training analytics. It is designed to serve web, mobile, and other client applications with a clean authenticated API, structured domain models, and analytics that can drive dashboards, progress screens, and coaching workflows.

## What This Backend Covers

The current backend supports the full MVP flow for a personal training app:

- User registration, login, token refresh, and authenticated profile access
- User profile and bodyweight tracking
- Exercise catalog browsing with search and filters
- Workout template planning
- Workout session logging with per-set tracking
- Automatic personal record detection
- Exercise progress analytics
- Mesocycles as optional training blocks
- Deload suggestions, muscle balance reports, and block-to-block comparisons
- Public client bootstrap metadata for frontend/mobile apps
- Aggregated user overview endpoint for app home/dashboard screens

## Architecture Overview

Core layers in the project:

- `app/api/` contains FastAPI routers and request dependencies
- `app/core/` contains configuration, database wiring, security, logging, analytics, and PR logic
- `app/models/` contains SQLAlchemy domain models
- `app/schemas/` contains Pydantic request/response contracts
- `alembic/` contains migrations
- `tests/` contains API, unit, and integration tests

The application currently uses:

- FastAPI
- SQLAlchemy 2.x
- PostgreSQL
- Alembic
- Pydantic Settings
- Uvicorn
- Pytest
- `uv`

## API Surface

### Public endpoints

- `GET /`
- `GET /health`
- `GET /db-test`
- `GET /db-query`
- `GET /meta/app-config`
- `POST /auth/register`
- `POST /auth/login`
- `POST /auth/refresh`

### Authenticated endpoints

- `GET /auth/me`
- `GET /users/me`
- `PATCH /users/me`
- `GET /users/me/overview`
- `GET /users/me/profile`
- `PUT /users/me/profile`
- `GET /users/me/body-weight-logs`
- `POST /users/me/body-weight-logs`
- `GET /users/me/body-weight-logs/{log_id}`
- `PATCH /users/me/body-weight-logs/{log_id}`
- `DELETE /users/me/body-weight-logs/{log_id}`
- `GET /exercises`
- `GET /exercises/filters`
- `GET /exercises/{exercise_id}`
- `GET /workout-templates`
- `POST /workout-templates`
- `GET /workout-templates/{template_id}`
- `PATCH /workout-templates/{template_id}`
- `DELETE /workout-templates/{template_id}`
- `GET /workout-templates/{template_id}/exercises`
- `POST /workout-templates/{template_id}/exercises`
- `GET /workout-templates/{template_id}/exercises/{template_exercise_id}`
- `PATCH /workout-templates/{template_id}/exercises/{template_exercise_id}`
- `DELETE /workout-templates/{template_id}/exercises/{template_exercise_id}`
- `GET /workout-sessions`
- `POST /workout-sessions`
- `GET /workout-sessions/{session_id}`
- `PATCH /workout-sessions/{session_id}`
- `DELETE /workout-sessions/{session_id}`
- `GET /workout-sessions/{session_id}/sets`
- `POST /workout-sessions/{session_id}/sets`
- `GET /workout-sessions/{session_id}/sets/{set_id}`
- `PATCH /workout-sessions/{session_id}/sets/{set_id}`
- `DELETE /workout-sessions/{session_id}/sets/{set_id}`
- `GET /personal-records`
- `GET /personal-records/{record_id}`
- `GET /progress/{exercise_id}`
- `GET /analytics/muscle-balance`
- `GET /mesocycles`
- `POST /mesocycles`
- `GET /mesocycles/{mesocycle_id}`
- `GET /mesocycles/{mesocycle_id}/analytics`
- `PATCH /mesocycles/{mesocycle_id}`
- `DELETE /mesocycles/{mesocycle_id}`

## Frontend and Mobile Integration

The backend now includes client-facing integration aids intended to reduce frontend complexity:

- Configurable CORS support for local web and hybrid mobile clients
- `GET /meta/app-config` for bootstrapping app-level client configuration
- Standardized error metadata with `message`, `status_code`, and `path`
- `GET /users/me/overview` for home-screen/dashboard aggregation
- OpenAPI docs at `/docs` and `/redoc`

Detailed frontend/mobile documentation is available in [docs/FRONTEND_INTEGRATION.md](/mnt/NewVolume/Programming/Python/FastApi_Project/docs/FRONTEND_INTEGRATION.md).

## Authentication Model

Authentication is JWT-based:

- Access token: bearer token for authenticated requests
- Refresh token: exchanged through `POST /auth/refresh`
- Access token lifetime is returned by the API in seconds
- Refresh token lifetime is returned by the API in seconds

Authenticated requests must include:

```http
Authorization: Bearer <access_token>
```

## Error Contract

Most errors now expose a frontend-friendly structure:

```json
{
  "detail": "Workout session not found",
  "message": "Workout session not found",
  "status_code": 404,
  "path": "/workout-sessions/999"
}
```

Validation errors also include `field_errors` so clients can map failures to form inputs.

## Local Development

### Prerequisites

- Python 3.11+
- `uv`
- Docker and Docker Compose

### Setup

1. Install dependencies

```bash
uv sync
```

2. Create environment variables

```bash
cp .env.example .env
```

3. Start PostgreSQL, run migrations, and launch the API

```bash
uv run start
```

4. Optional database reset and reseed

```bash
uv run start --reset
```

Default local URLs:

- API: `http://localhost:8000`
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`
- Adminer: `http://localhost:8080`

## Environment Variables

Minimum relevant configuration:

```env
APP_NAME=Athelix API
APP_VERSION=0.1.0
DEBUG=True

DATABASE_HOST=localhost
DATABASE_PORT=5432
DATABASE_NAME=app_db
DATABASE_USER=postgres
DATABASE_PASSWORD=postgres

JWT_SECRET_KEY=replace-with-a-long-random-secret-at-least-32-characters
JWT_REFRESH_SECRET_KEY=replace-with-a-different-long-random-secret
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

CORS_ALLOWED_ORIGINS=http://localhost:3000,http://localhost:5173,http://127.0.0.1:3000,http://127.0.0.1:5173,capacitor://localhost,ionic://localhost
CORS_ALLOW_CREDENTIALS=True
CORS_ALLOWED_METHODS=*
CORS_ALLOWED_HEADERS=*
```

## Database and Migrations

Apply migrations:

```bash
uv run alembic upgrade head
```

Create a new migration:

```bash
uv run alembic revision --autogenerate -m "describe_change"
```

## Running Tests

Run the full suite:

```bash
UV_CACHE_DIR=/tmp/uv-cache uv run pytest
```

Run a focused suite:

```bash
UV_CACHE_DIR=/tmp/uv-cache uv run pytest tests/test_api.py tests/test_users.py
```

Note: the repository includes PostgreSQL connectivity tests that require a running database on the configured host and port.

## Current Product Review

From an end-user perspective, the backend now covers the expected MVP flows for:

- Account onboarding
- Profile setup
- Exercise discovery
- Training plan creation
- Session logging
- Progress review
- PR visibility
- Optional structured mesocycle planning
- Analytics-driven coaching cues

Likely next-phase features, depending on product scope:

- Password reset and email verification
- Social features or coach-athlete collaboration
- Notifications and reminders
- Media/file uploads
- Admin tooling and moderation
- Background jobs for heavier analytics or reporting
- Offline sync conflict resolution for mobile apps

Those are product expansion items rather than obvious gaps in the current MVP backend.

## Project Structure

```text
app/
  api/
  core/
  models/
  schemas/
alembic/
db_init/
scripts/
sql/
tests/
docs/
```

## Documentation

- Project overview: [README.md](README.md)
- Frontend/mobile handoff: [docs/FRONTEND_INTEGRATION.md](docs/FRONTEND_INTEGRATION.md)
- Tests guide: [tests/README.md](tests/README.md)
