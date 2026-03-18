import pytest

from app.core.config import settings

pytestmark = pytest.mark.asyncio


class TestRegistrationEndpoint:
    async def test_register_user_returns_token_and_user(self, client):
        response = await client.post(
            "/auth/register",
            json={
                "username": "athlete_one",
                "email": "athlete@example.com",
                "password": "StrongPass123",
            },
        )

        assert response.status_code == 201

        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert data["expires_in"] == settings.access_token_expire_minutes * 60
        assert data["user"]["username"] == "athlete_one"
        assert data["user"]["email"] == "athlete@example.com"

    async def test_register_user_rejects_duplicate_email(self, client):
        payload = {
            "username": "athlete_one",
            "email": "athlete@example.com",
            "password": "StrongPass123",
        }

        assert (await client.post("/auth/register", json=payload)).status_code == 201

        duplicate_response = await client.post(
            "/auth/register",
            json={
                "username": "athlete_two",
                "email": payload["email"],
                "password": payload["password"],
            },
        )

        assert duplicate_response.status_code == 409
        assert duplicate_response.json()["detail"] == "Email is already registered"


class TestLoginEndpoint:
    async def test_login_returns_token_for_valid_credentials(self, client):
        registration_payload = {
            "username": "athlete_one",
            "email": "athlete@example.com",
            "password": "StrongPass123",
        }
        await client.post("/auth/register", json=registration_payload)

        response = await client.post(
            "/auth/login",
            json={
                "email": registration_payload["email"],
                "password": registration_payload["password"],
            },
        )

        assert response.status_code == 200

        data = response.json()
        assert "access_token" in data
        assert data["user"]["email"] == registration_payload["email"]

    async def test_login_rejects_invalid_credentials(self, client):
        response = await client.post(
            "/auth/login",
            json={
                "email": "unknown@example.com",
                "password": "WrongPass123",
            },
        )

        assert response.status_code == 401
        assert response.json()["detail"] == "Invalid email or password"


class TestAuthenticatedEndpoint:
    async def test_get_me_returns_current_user(self, client):
        register_response = await client.post(
            "/auth/register",
            json={
                "username": "athlete_one",
                "email": "athlete@example.com",
                "password": "StrongPass123",
            },
        )
        token = register_response.json()["access_token"]

        response = await client.get(
            "/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["username"] == "athlete_one"
        assert data["email"] == "athlete@example.com"
