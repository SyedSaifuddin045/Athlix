"""Tests for FastAPI endpoints."""

import pytest

pytestmark = pytest.mark.asyncio


class TestRootEndpoint:
    """Tests for the root endpoint."""

    async def test_root_response(self, client):
        response = await client.get("/")

        assert response.status_code == 200

        data = response.json()

        assert "message" in data
        assert "Welcome to Athelix API" in data["message"]

        assert "version" in data
        assert data["version"] == "0.1.0"


class TestHealthEndpoint:
    """Tests for the health endpoint."""

    async def test_health_response(self, client):
        response = await client.get("/health")

        assert response.status_code == 200

        data = response.json()

        assert data["status"] == "healthy"
        assert data["version"] == "0.1.0"
        assert "database_url" not in data


class TestMetaEndpoint:
    """Tests for public app bootstrap metadata."""

    async def test_app_config_response_structure(self, client):
        response = await client.get("/meta/app-config")

        assert response.status_code == 200
        data = response.json()

        assert data["app_name"] == "Athelix API"
        assert data["version"] == "0.1.0"
        assert data["auth"]["token_type"] == "bearer"
        assert "epley" in data["supported_values"]["e1rm_formulas"]
        assert "estimated_1rm" in data["supported_values"]["personal_record_types"]
        assert "strength" in data["supported_values"]["mesocycle_goals"]


class TestDatabaseTestEndpoint:
    """Tests for /db-test endpoint."""

    async def test_db_test_response_structure(self, client):
        response = await client.get("/db-test")

        assert response.status_code == 200

        data = response.json()

        assert "status" in data
        assert data["status"] in ["success", "error"]

        assert "message" in data
        assert isinstance(data["message"], str)


class TestDatabaseQueryEndpoint:
    """Tests for /db-query endpoint."""

    async def test_db_query_response_structure(self, client):
        response = await client.get("/db-query")

        assert response.status_code == 200

        data = response.json()

        assert "status" in data
        assert data["status"] in ["success", "error"]

        assert "message" in data
        assert isinstance(data["message"], str)


class TestAPIEndpoints:
    """Integration tests across API endpoints."""

    endpoints = ["/", "/health", "/db-test", "/db-query", "/meta/app-config"]

    async def test_all_endpoints_return_success(self, client):
        for endpoint in self.endpoints:
            response = await client.get(endpoint)
            assert response.status_code == 200, f"{endpoint} returned {response.status_code}"

    async def test_all_endpoints_return_json(self, client):
        for endpoint in self.endpoints:
            response = await client.get(endpoint)

            assert response.headers["content-type"].startswith("application/json")

            data = response.json()
            assert isinstance(data, dict)

    async def test_cors_preflight_returns_allowed_origin(self, client):
        response = await client.options(
            "/meta/app-config",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "GET",
            },
        )

        assert response.status_code == 200
        assert response.headers["access-control-allow-origin"] == "http://localhost:3000"


class TestErrorHandling:
    """Tests for API error behavior."""

    async def test_invalid_endpoint_returns_404(self, client):
        response = await client.get("/invalid-endpoint")

        assert response.status_code == 404
        data = response.json()
        assert data["status_code"] == 404
        assert data["path"] == "/invalid-endpoint"

    async def test_method_not_allowed(self, client):
        response = await client.post("/")

        assert response.status_code == 405
        data = response.json()
        assert data["status_code"] == 405
        assert data["path"] == "/"
