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
        assert "database_url" in data
        assert isinstance(data["database_url"], str)


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

    endpoints = ["/", "/health", "/db-test", "/db-query"]

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


class TestErrorHandling:
    """Tests for API error behavior."""

    async def test_invalid_endpoint_returns_404(self, client):
        response = await client.get("/invalid-endpoint")

        assert response.status_code == 404

    async def test_method_not_allowed(self, client):
        response = await client.post("/")

        assert response.status_code == 405
