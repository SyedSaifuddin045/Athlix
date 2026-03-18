from datetime import date, datetime, timezone

import pytest
from sqlalchemy.orm import Session

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
def seeded_exercise(client, test_db):
    with Session(test_db) as session:
        session.add(
            Exercise(
                id="bench-press",
                name="Bench Press",
                body_part="chest",
                equipment="barbell",
                gif_url="https://example.com/bench-press.gif",
                target="pectorals",
            )
        )
        session.commit()

    return {"bench_press": "bench-press"}


class TestProgressEndpoint:
    async def test_progress_endpoint_returns_e1rm_volume_overload_and_streaks(
        self,
        client,
        seeded_exercise,
    ):
        auth_data = await register_user(client)
        headers = {"Authorization": f"Bearer {auth_data['access_token']}"}

        first_session = await client.post(
            "/workout-sessions",
            json={
                "name": "Bench Day 1",
                "started_at": "2026-03-10T06:00:00Z",
                "finished_at": "2026-03-10T07:00:00Z",
                "is_completed": True,
            },
            headers=headers,
        )
        second_session = await client.post(
            "/workout-sessions",
            json={
                "name": "Bench Day 2",
                "started_at": "2026-03-17T06:00:00Z",
                "finished_at": "2026-03-17T07:00:00Z",
                "is_completed": True,
            },
            headers=headers,
        )
        assert first_session.status_code == 201
        assert second_session.status_code == 201

        first_session_id = first_session.json()["id"]
        second_session_id = second_session.json()["id"]

        first_set = await client.post(
            f"/workout-sessions/{first_session_id}/sets",
            json={
                "exercise_id": seeded_exercise["bench_press"],
                "set_number": 1,
                "set_type": "working",
                "reps": 5,
                "weight_kg": 100,
            },
            headers=headers,
        )
        second_set = await client.post(
            f"/workout-sessions/{first_session_id}/sets",
            json={
                "exercise_id": seeded_exercise["bench_press"],
                "set_number": 2,
                "set_type": "working",
                "reps": 8,
                "weight_kg": 90,
            },
            headers=headers,
        )
        third_set = await client.post(
            f"/workout-sessions/{second_session_id}/sets",
            json={
                "exercise_id": seeded_exercise["bench_press"],
                "set_number": 1,
                "set_type": "working",
                "reps": 5,
                "weight_kg": 110,
            },
            headers=headers,
        )
        assert first_set.status_code == 201
        assert second_set.status_code == 201
        assert third_set.status_code == 201

        response = await client.get(
            f"/progress/{seeded_exercise['bench_press']}",
            params={
                "formula": "lombardi",
                "reference_date": date(2026, 3, 17).isoformat(),
            },
            headers=headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["exercise_id"] == seeded_exercise["bench_press"]
        assert data["exercise_name"] == "Bench Press"
        assert data["default_formula"] == "lombardi"
        assert len(data["e1rm_history"]) == 2
        assert data["e1rm_history"][0]["volume_load"] == 1220
        assert data["e1rm_history"][1]["default_e1rm"] == pytest.approx(129.21, abs=0.01)
        assert data["e1rm_history"][1]["formulas"]["epley"] == pytest.approx(128.33, abs=0.01)

        assert [item["volume_load"] for item in data["weekly_volume_history"]] == [1220, 550]
        assert len(data["progressive_overload"]) == 1
        overload = data["progressive_overload"][0]
        assert overload["improved_metrics"] == ["best_weight", "estimated_1rm"]
        assert overload["best_weight_delta"] == 10

        streaks = data["workout_streaks"]
        assert streaks["current_daily_streak"] == 1
        assert streaks["current_weekly_streak"] == 2

    async def test_progress_endpoint_rejects_unknown_formula(self, client, seeded_exercise):
        auth_data = await register_user(client)
        headers = {"Authorization": f"Bearer {auth_data['access_token']}"}

        response = await client.get(
            f"/progress/{seeded_exercise['bench_press']}",
            params={"formula": "invalid"},
            headers=headers,
        )

        assert response.status_code == 422
        assert response.json()["detail"] == "Unsupported e1RM formula"
