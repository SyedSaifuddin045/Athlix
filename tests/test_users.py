import pytest

pytestmark = pytest.mark.asyncio


async def register_user(
    client,
    username: str = "athlete_one",
    email: str = "athlete@example.com",
    password: str = "StrongPass123",
):
    response = await client.post(
        "/auth/register",
        json={
            "username": username,
            "email": email,
            "password": password,
        },
    )
    assert response.status_code == 201
    return response.json()


class TestCurrentUserEndpoints:
    async def test_get_current_user_details(self, client):
        auth_data = await register_user(client)

        response = await client.get(
            "/users/me",
            headers={"Authorization": f"Bearer {auth_data['access_token']}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["username"] == "athlete_one"
        assert data["email"] == "athlete@example.com"

    async def test_update_current_user(self, client):
        auth_data = await register_user(client)

        response = await client.patch(
            "/users/me",
            json={
                "username": "athlete_updated",
                "email": "updated@example.com",
            },
            headers={"Authorization": f"Bearer {auth_data['access_token']}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["username"] == "athlete_updated"
        assert data["email"] == "updated@example.com"

    async def test_update_current_user_rejects_duplicate_email(self, client):
        first_user = await register_user(client)
        await register_user(
            client,
            username="athlete_two",
            email="athlete.two@example.com",
        )

        response = await client.patch(
            "/users/me",
            json={"email": "athlete.two@example.com"},
            headers={"Authorization": f"Bearer {first_user['access_token']}"},
        )

        assert response.status_code == 409
        assert response.json()["detail"] == "Email is already registered"


class TestUserProfileEndpoints:
    async def test_get_profile_returns_404_when_missing(self, client):
        auth_data = await register_user(client)

        response = await client.get(
            "/users/me/profile",
            headers={"Authorization": f"Bearer {auth_data['access_token']}"},
        )

        assert response.status_code == 404
        assert response.json()["detail"] == "User profile not found"

    async def test_upsert_profile_creates_and_updates_profile(self, client):
        auth_data = await register_user(client)
        headers = {"Authorization": f"Bearer {auth_data['access_token']}"}

        create_response = await client.put(
            "/users/me/profile",
            json={
                "display_name": "Athlete One",
                "height_cm": 180,
                "weight_kg": 82.5,
                "preferred_unit": "metric",
            },
            headers=headers,
        )

        assert create_response.status_code == 200
        created_profile = create_response.json()
        assert created_profile["display_name"] == "Athlete One"
        assert created_profile["preferred_unit"] == "metric"

        update_response = await client.put(
            "/users/me/profile",
            json={
                "display_name": "Updated Athlete",
                "height_cm": 181,
                "weight_kg": 80.2,
                "fitness_level": "intermediate",
                "preferred_unit": "metric",
            },
            headers=headers,
        )

        assert update_response.status_code == 200
        updated_profile = update_response.json()
        assert updated_profile["display_name"] == "Updated Athlete"
        assert updated_profile["height_cm"] == 181
        assert updated_profile["fitness_level"] == "intermediate"


class TestBodyWeightLogEndpoints:
    async def test_body_weight_log_crud_flow(self, client):
        auth_data = await register_user(client)
        headers = {"Authorization": f"Bearer {auth_data['access_token']}"}

        first_create = await client.post(
            "/users/me/body-weight-logs",
            json={
                "weight_kg": 82.5,
                "logged_at": "2026-03-10",
                "notes": "Morning weigh-in",
            },
            headers=headers,
        )
        second_create = await client.post(
            "/users/me/body-weight-logs",
            json={
                "weight_kg": 81.8,
                "logged_at": "2026-03-12",
                "notes": "After deload",
            },
            headers=headers,
        )

        assert first_create.status_code == 201
        assert second_create.status_code == 201

        first_log = first_create.json()

        list_response = await client.get(
            "/users/me/body-weight-logs",
            headers=headers,
        )
        assert list_response.status_code == 200
        logs = list_response.json()
        assert len(logs) == 2
        assert logs[0]["logged_at"] == "2026-03-12"
        assert logs[1]["logged_at"] == "2026-03-10"

        get_response = await client.get(
            f"/users/me/body-weight-logs/{first_log['id']}",
            headers=headers,
        )
        assert get_response.status_code == 200
        assert get_response.json()["notes"] == "Morning weigh-in"

        update_response = await client.patch(
            f"/users/me/body-weight-logs/{first_log['id']}",
            json={
                "weight_kg": 82.1,
                "notes": "Updated note",
            },
            headers=headers,
        )
        assert update_response.status_code == 200
        updated_log = update_response.json()
        assert updated_log["weight_kg"] == 82.1
        assert updated_log["notes"] == "Updated note"

        delete_response = await client.delete(
            f"/users/me/body-weight-logs/{first_log['id']}",
            headers=headers,
        )
        assert delete_response.status_code == 204

        missing_response = await client.get(
            f"/users/me/body-weight-logs/{first_log['id']}",
            headers=headers,
        )
        assert missing_response.status_code == 404
        assert missing_response.json()["detail"] == "Body weight log not found"
