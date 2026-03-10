# Test Suite Documentation

This directory contains all tests for the Athelix FastAPI application.

## Test Structure

```
tests/
├── __init__.py              # Test package initialization
├── conftest.py              # Pytest fixtures and configuration
├── test_database.py         # Database connection tests
├── test_api.py              # API endpoint tests
└── test_config.py           # Configuration tests
```

## Running Tests

### Run all tests
```bash
pytest
# or with uv
uv run pytest
```

### Run specific test file
```bash
pytest tests/test_api.py
# or
uv run pytest tests/test_api.py
```

### Run specific test class
```bash
pytest tests/test_api.py::TestRootEndpoint
# or
uv run pytest tests/test_api.py::TestRootEndpoint
```

### Run specific test function
```bash
pytest tests/test_api.py::TestRootEndpoint::test_root_returns_200
# or
uv run pytest tests/test_api.py::TestRootEndpoint::test_root_returns_200
```

### Run with verbose output
```bash
pytest -v
# or
uv run pytest -v
```

### Run with detailed output and short traceback
```bash
pytest -vv --tb=short
# or
uv run pytest -vv --tb=short
```

## Test Markers

The test suite uses pytest markers to categorize tests:

### Run only unit tests (fast)
```bash
pytest -m "not integration"
# or
uv run pytest -m "not integration"
```

### Run only integration tests (requires services)
```bash
pytest -m integration
# or
uv run pytest -m integration
```

### Run all tests
```bash
pytest
# or
uv run pytest
```

## Test Categories

### Database Tests (`test_database.py`)

**Unit Tests (fast, no external services required):**
- Database URL configuration validation
- SQLAlchemy engine creation
- Session factory instantiation
- Dependency injection setup

**Integration Tests (requires running PostgreSQL):**
- PostgreSQL connection verification
- Query execution
- User and database information retrieval

### API Endpoint Tests (`test_api.py`)

- Root endpoint (`GET /`)
- Health check endpoint (`GET /health`)
- Database test endpoint (`GET /db-test`)
- Database query endpoint (`GET /db-query`)
- Error handling (404, 405)
- Response format validation

### Configuration Tests (`test_config.py`)

- Settings instance validation
- Database URL format and content verification
- Environment variable loading

## Fixtures

Common fixtures defined in `conftest.py`:

### `client`
- FastAPI TestClient with test database
- Automatically cleans up dependency overrides
- Use this for API endpoint tests

```python
def test_something(client):
    response = client.get("/")
    assert response.status_code == 200
```

### `db_session`
- SQLAlchemy session for database operations
- Automatically rolls back transactions
- Use this for database operation tests

```python
def test_something(db_session):
    # Use db_session for database operations
    result = db_session.execute(...)
```

### `test_db`
- In-memory SQLite database for testing
- Session-scoped, reused across tests

## Coverage Report

Generate a coverage report:

```bash
pytest --cov=app --cov-report=html
# or
uv run pytest --cov=app --cov-report=html
```

Then open `htmlcov/index.html` in a browser to view the report.

## Best Practices

1. **Test naming**: Use descriptive names that explain what's being tested
2. **Test organization**: Group related tests in classes
3. **Fixtures**: Use fixtures for setup/teardown and shared state
4. **Markers**: Use markers to categorize test types (unit vs integration)
5. **Assertions**: Use clear, specific assertions with helpful error messages
6. **Docstrings**: Add docstrings to test functions explaining what they test

## Troubleshooting

### Tests fail with "ModuleNotFoundError"
- Make sure you're running pytest from the project root
- Ensure the `app` package is importable: `python -c "import app"`

### Database tests fail with connection error
- Ensure PostgreSQL is running: `docker-compose ps`
- Check database credentials in `.env` file
- For unit tests only, use: `pytest -m "not integration"`

### TestClient fixture issues
- Ensure httpx is installed: `uv pip install httpx`
- Check that starlette is installed: `uv pip install starlette`

## Continuous Integration

Tests are designed to run in CI/CD pipelines. For fastest feedback:

```bash
# Unit tests only (no external services needed)
pytest -m "not integration" --tb=short

# Or full test suite (with services)
pytest --tb=short
```

## Contributing

When adding new features:
1. Write tests first (TDD approach)
2. Ensure tests pass with `pytest`
3. Add appropriate markers (@pytest.mark.integration, etc.)
4. Update this README if needed
5. Maintain test organization by test type
