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
def seeded_exercise(client, test_db):
    with Session(test_db) as session:
        session.add(
            Exercise(
                id="squat",
                name="Back Squat",
                body_part="upper legs",
                equipment="barbell",
                gif_url="https://example.com/squat.gif",
                target="quads",
            )
        )
        session.commit()

    return {"squat": "squat"}


@pytest.fixture
def seeded_exercises(client, test_db):
    with Session(test_db) as session:
        session.add_all(
            [
                Exercise(
                    id="squat",
                    name="Back Squat",
                    body_part="upper legs",
                    equipment="barbell",
                    gif_url="https://example.com/squat.gif",
                    target="quads",
                ),
                Exercise(
                    id="bench-press",
                    name="Bench Press",
                    body_part="chest",
                    equipment="barbell",
                    gif_url="https://example.com/bench.gif",
                    target="pectorals",
                ),
            ]
        )
        session.commit()

    return {
        "squat": "squat",
        "bench_press": "bench-press",
    }


class TestMesocycleEndpoints:
    async def test_mesocycle_crud_flow_with_linked_sessions(self, client, seeded_exercise):
        auth_data = await register_user(client)
        headers = {"Authorization": f"Bearer {auth_data['access_token']}"}

        create_response = await client.post(
            "/mesocycles",
            json={
                "name": "Strength Block 1",
                "goal": "strength",
                "started_on": "2026-03-01",
                "ended_on": "2026-04-12",
                "weeks": 6,
                "notes": "Optional structured block",
            },
            headers=headers,
        )
        assert create_response.status_code == 201
        mesocycle = create_response.json()
        assert mesocycle["goal"] == "strength"

        session_response = await client.post(
            "/workout-sessions",
            json={
                "mesocycle_id": mesocycle["id"],
                "name": "Lower Day",
                "started_at": "2026-03-02T06:00:00Z",
                "finished_at": "2026-03-02T07:00:00Z",
                "is_completed": True,
            },
            headers=headers,
        )
        assert session_response.status_code == 201

        list_response = await client.get("/mesocycles", headers=headers)
        assert list_response.status_code == 200
        assert len(list_response.json()) == 1

        detail_response = await client.get(
            f"/mesocycles/{mesocycle['id']}",
            headers=headers,
        )
        assert detail_response.status_code == 200
        detail = detail_response.json()
        assert detail["id"] == mesocycle["id"]
        assert len(detail["sessions"]) == 1
        assert detail["sessions"][0]["mesocycle_id"] == mesocycle["id"]

        update_response = await client.patch(
            f"/mesocycles/{mesocycle['id']}",
            json={
                "goal": "hypertrophy",
                "weeks": 7,
            },
            headers=headers,
        )
        assert update_response.status_code == 200
        updated = update_response.json()
        assert updated["goal"] == "hypertrophy"
        assert updated["weeks"] == 7

        delete_response = await client.delete(
            f"/mesocycles/{mesocycle['id']}",
            headers=headers,
        )
        assert delete_response.status_code == 204

        missing_response = await client.get(
            f"/mesocycles/{mesocycle['id']}",
            headers=headers,
        )
        assert missing_response.status_code == 404
        assert missing_response.json()["detail"] == "Mesocycle not found"

    async def test_mesocycle_validates_payload(self, client, seeded_exercise):
        auth_data = await register_user(client)
        headers = {"Authorization": f"Bearer {auth_data['access_token']}"}

        invalid_goal = await client.post(
            "/mesocycles",
            json={
                "name": "Bad Block",
                "goal": "powerbuilding",
                "started_on": "2026-03-01",
            },
            headers=headers,
        )
        assert invalid_goal.status_code == 422
        assert invalid_goal.json()["detail"] == "Unsupported mesocycle goal"

        invalid_dates = await client.post(
            "/mesocycles",
            json={
                "name": "Bad Dates",
                "goal": "strength",
                "started_on": "2026-03-10",
                "ended_on": "2026-03-01",
            },
            headers=headers,
        )
        assert invalid_dates.status_code == 422
        assert invalid_dates.json()["detail"] == "Mesocycle end date cannot be before the start date"

    async def test_mesocycle_analytics_returns_block_comparison_and_deload_signal(
        self,
        client,
        seeded_exercises,
    ):
        auth_data = await register_user(client)
        headers = {"Authorization": f"Bearer {auth_data['access_token']}"}

        previous_mesocycle = await client.post(
            "/mesocycles",
            json={
                "name": "Strength Block 0",
                "goal": "strength",
                "started_on": "2026-01-05",
                "ended_on": "2026-02-01",
                "weeks": 4,
            },
            headers=headers,
        )
        current_mesocycle = await client.post(
            "/mesocycles",
            json={
                "name": "Strength Block 1",
                "goal": "strength",
                "started_on": "2026-02-02",
                "ended_on": "2026-03-01",
                "weeks": 4,
            },
            headers=headers,
        )
        assert previous_mesocycle.status_code == 201
        assert current_mesocycle.status_code == 201

        previous_mesocycle_id = previous_mesocycle.json()["id"]
        current_mesocycle_id = current_mesocycle.json()["id"]

        previous_session = await client.post(
            "/workout-sessions",
            json={
                "mesocycle_id": previous_mesocycle_id,
                "name": "Previous Block Day",
                "started_at": "2026-01-06T06:00:00Z",
                "finished_at": "2026-01-06T07:00:00Z",
                "is_completed": True,
            },
            headers=headers,
        )
        first_current_session = await client.post(
            "/workout-sessions",
            json={
                "mesocycle_id": current_mesocycle_id,
                "name": "Current Block Day 1",
                "started_at": "2026-02-03T06:00:00Z",
                "finished_at": "2026-02-03T07:00:00Z",
                "is_completed": True,
            },
            headers=headers,
        )
        second_current_session = await client.post(
            "/workout-sessions",
            json={
                "mesocycle_id": current_mesocycle_id,
                "name": "Current Block Day 2",
                "started_at": "2026-02-10T06:00:00Z",
                "finished_at": "2026-02-10T07:00:00Z",
                "is_completed": True,
            },
            headers=headers,
        )
        assert previous_session.status_code == 201
        assert first_current_session.status_code == 201
        assert second_current_session.status_code == 201

        previous_session_id = previous_session.json()["id"]
        first_current_session_id = first_current_session.json()["id"]
        second_current_session_id = second_current_session.json()["id"]

        for payload in (
            {
                "session_id": previous_session_id,
                "exercise_id": seeded_exercises["bench_press"],
                "set_number": 1,
                "set_type": "working",
                "reps": 5,
                "weight_kg": 100,
                "rpe": 8.0,
            },
            {
                "session_id": previous_session_id,
                "exercise_id": seeded_exercises["squat"],
                "set_number": 2,
                "set_type": "working",
                "reps": 5,
                "weight_kg": 140,
                "rpe": 8.2,
            },
            {
                "session_id": first_current_session_id,
                "exercise_id": seeded_exercises["bench_press"],
                "set_number": 1,
                "set_type": "working",
                "reps": 5,
                "weight_kg": 105,
                "rpe": 8.7,
            },
            {
                "session_id": first_current_session_id,
                "exercise_id": seeded_exercises["squat"],
                "set_number": 2,
                "set_type": "working",
                "reps": 5,
                "weight_kg": 145,
                "rpe": 8.8,
            },
            {
                "session_id": second_current_session_id,
                "exercise_id": seeded_exercises["bench_press"],
                "set_number": 1,
                "set_type": "working",
                "reps": 5,
                "weight_kg": 110,
                "rpe": 8.9,
            },
        ):
            response = await client.post(
                f"/workout-sessions/{payload['session_id']}/sets",
                json={key: value for key, value in payload.items() if key != "session_id"},
                headers=headers,
            )
            assert response.status_code == 201

        analytics_response = await client.get(
            f"/mesocycles/{current_mesocycle_id}/analytics",
            params={"formula": "epley"},
            headers=headers,
        )

        assert analytics_response.status_code == 200
        data = analytics_response.json()
        assert data["mesocycle"]["id"] == current_mesocycle_id
        assert data["previous_mesocycle"]["id"] == previous_mesocycle_id
        assert data["current_block_summary"]["completed_sessions"] == 2
        assert data["comparison_to_previous"]["total_volume_load_delta"] == 600
        assert data["deload_suggestion"]["is_recommended"] is True
        assert data["deload_suggestion"]["current_consecutive_high_weeks"] == 2
        bench_comparison = next(
            item for item in data["exercise_comparisons"] if item["exercise_id"] == seeded_exercises["bench_press"]
        )
        assert bench_comparison["best_e1rm_delta"] == pytest.approx(11.66, abs=0.01)
        assert data["muscle_balance"]["weeks_in_scope"] == 4
        pectorals = next(
            item for item in data["muscle_balance"]["items"] if item["muscle_group"] == "pectorals"
        )
        assert pectorals["completed_sets"] == 2
        assert pectorals["meets_minimum"] is False

    async def test_mesocycle_respects_user_ownership(self, client, seeded_exercise):
        first_user = await register_user(client)
        second_user = await register_user(
            client,
            username="athlete_two",
            email="athlete.two@example.com",
        )

        first_headers = {"Authorization": f"Bearer {first_user['access_token']}"}
        second_headers = {"Authorization": f"Bearer {second_user['access_token']}"}

        create_response = await client.post(
            "/mesocycles",
            json={
                "name": "Private Block",
                "goal": "strength",
                "started_on": "2026-03-01",
            },
            headers=first_headers,
        )
        assert create_response.status_code == 201
        mesocycle_id = create_response.json()["id"]

        get_response = await client.get(
            f"/mesocycles/{mesocycle_id}",
            headers=second_headers,
        )
        assert get_response.status_code == 404
        assert get_response.json()["detail"] == "Mesocycle not found"
