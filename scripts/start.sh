#!/usr/bin/env bash
set -e

ENV_FILE=.env
RESET_DB=false

# -------- Parse arguments --------
for arg in "$@"; do
  case $arg in
    --reset)
      RESET_DB=true
      shift
      ;;
  esac
done

# -------- Load environment variables --------
set -a
source "$ENV_FILE"
set +a

# -------- Handle database reset --------
if [ "$RESET_DB" = true ]; then
  echo "Reset flag detected → removing containers and volumes..."
  docker-compose --env-file "$ENV_FILE" down -v
else
  echo "Starting containers without resetting database..."
fi

# -------- Start services --------
echo "Starting containers..."
docker-compose --env-file "$ENV_FILE" up -d

# -------- Wait for database --------
echo "Waiting for database to become ready..."
until docker exec "$POSTGRES_CONTAINER_NAME" pg_isready -U "$POSTGRES_USER" >/dev/null 2>&1; do
  sleep 2
done

# -------- Confirm API startup --------
echo "Waiting for API to start..."
until docker-compose --env-file "$ENV_FILE" exec -T app python -c "from urllib.request import urlopen; urlopen('http://127.0.0.1:8000/health').read()" >/dev/null 2>&1; do
  sleep 2
done

# -------- Seed database --------
if [ "$RESET_DB" = true ]; then
  echo "Seeding database..."
  uv run python -m scripts.seed_exercises_data
fi

echo "API is running at http://localhost:8000"
echo "Swagger UI: http://localhost:8000/docs"
