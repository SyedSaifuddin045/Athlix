from sqlalchemy.orm import Session
import pytest

from app.models.exercise import Exercise

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


@pytest.fixture
def seeded_exercises(client, test_db):
    with Session(test_db) as session:
        session.add_all(
            [
                Exercise(
                    id="bench-press",
                    name="Bench Press",
                    body_part="chest",
                    equipment="barbell",
                    gif_url="https://example.com/bench.gif",
                    target="pectorals",
                ),
                Exercise(
                    id="squat",
                    name="Back Squat",
                    body_part="upper legs",
                    equipment="barbell",
                    gif_url="https://example.com/squat.gif",
                    target="quads",
                ),
            ]
        )
        session.commit()

    return {
        "bench_press": "bench-press",
        "squat": "squat",
    }


class TestAnalyticsEndpoints:
    async def test_muscle_balance_report_uses_recent_completed_working_sets(
        self,
        client,
        seeded_exercises,
    ):
        auth_data = await register_user(client)
        headers = {"Authorization": f"Bearer {auth_data['access_token']}"}

        session_response = await client.post(
            "/workout-sessions",
            json={
                "name": "Upper Day",
                "started_at": "2026-03-10T06:00:00Z",
                "finished_at": "2026-03-10T07:00:00Z",
                "is_completed": True,
            },
            headers=headers,
        )
        assert session_response.status_code == 201
        session_id = session_response.json()["id"]

        for payload in (
            {
                "exercise_id": seeded_exercises["bench_press"],
                "set_number": 1,
                "set_type": "working",
                "reps": 5,
                "weight_kg": 100,
            },
            {
                "exercise_id": seeded_exercises["bench_press"],
                "set_number": 2,
                "set_type": "working",
                "reps": 8,
                "weight_kg": 90,
            },
            {
                "exercise_id": seeded_exercises["squat"],
                "set_number": 3,
                "set_type": "warmup",
                "reps": 5,
                "weight_kg": 60,
            },
        ):
            response = await client.post(
                f"/workout-sessions/{session_id}/sets",
                json=payload,
                headers=headers,
            )
            assert response.status_code == 201

        report_response = await client.get(
            "/analytics/muscle-balance",
            params={
                "weeks": 4,
                "reference_date": "2026-03-18",
            },
            headers=headers,
        )

        assert report_response.status_code == 200
        data = report_response.json()
        assert data["weeks_in_scope"] == 4
        assert len(data["items"]) == 1
        assert data["items"][0]["muscle_group"] == "pectorals"
        assert data["items"][0]["completed_sets"] == 2
        assert data["items"][0]["average_weekly_sets"] == 0.5
        assert data["items"][0]["meets_minimum"] is False

    async def test_muscle_balance_report_can_scope_to_mesocycle(
        self,
        client,
        seeded_exercises,
    ):
        auth_data = await register_user(client)
        headers = {"Authorization": f"Bearer {auth_data['access_token']}"}

        mesocycle_response = await client.post(
            "/mesocycles",
            json={
                "name": "Hypertrophy Block",
                "goal": "hypertrophy",
                "started_on": "2026-03-01",
                "ended_on": "2026-03-28",
                "weeks": 4,
            },
            headers=headers,
        )
        assert mesocycle_response.status_code == 201
        mesocycle_id = mesocycle_response.json()["id"]

        mesocycle_session = await client.post(
            "/workout-sessions",
            json={
                "mesocycle_id": mesocycle_id,
                "name": "Block Session",
                "started_at": "2026-03-04T06:00:00Z",
                "finished_at": "2026-03-04T07:00:00Z",
                "is_completed": True,
            },
            headers=headers,
        )
        regular_session = await client.post(
            "/workout-sessions",
            json={
                "name": "Outside Block Session",
                "started_at": "2026-03-11T06:00:00Z",
                "finished_at": "2026-03-11T07:00:00Z",
                "is_completed": True,
            },
            headers=headers,
        )
        assert mesocycle_session.status_code == 201
        assert regular_session.status_code == 201

        mesocycle_session_id = mesocycle_session.json()["id"]
        regular_session_id = regular_session.json()["id"]

        inside_set = await client.post(
            f"/workout-sessions/{mesocycle_session_id}/sets",
            json={
                "exercise_id": seeded_exercises["squat"],
                "set_number": 1,
                "set_type": "working",
                "reps": 5,
                "weight_kg": 140,
            },
            headers=headers,
        )
        outside_set = await client.post(
            f"/workout-sessions/{regular_session_id}/sets",
            json={
                "exercise_id": seeded_exercises["bench_press"],
                "set_number": 1,
                "set_type": "working",
                "reps": 5,
                "weight_kg": 100,
            },
            headers=headers,
        )
        assert inside_set.status_code == 201
        assert outside_set.status_code == 201

        report_response = await client.get(
            "/analytics/muscle-balance",
            params={"mesocycle_id": mesocycle_id},
            headers=headers,
        )

        assert report_response.status_code == 200
        data = report_response.json()
        assert data["weeks_in_scope"] == 4
        assert len(data["items"]) == 1
        assert data["items"][0]["muscle_group"] == "quads"
        assert data["items"][0]["completed_sets"] == 1
