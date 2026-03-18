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
def seeded_exercises(client, test_db):
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


class TestPersonalRecordTracking:
    async def test_personal_records_are_created_when_session_is_completed(
        self,
        client,
        seeded_exercises,
    ):
        auth_data = await register_user(client)
        headers = {"Authorization": f"Bearer {auth_data['access_token']}"}

        session_response = await client.post(
            "/workout-sessions",
            json={
                "name": "Push Day",
                "started_at": "2026-03-18T06:00:00Z",
            },
            headers=headers,
        )
        assert session_response.status_code == 201
        workout_session = session_response.json()

        first_set = await client.post(
            f"/workout-sessions/{workout_session['id']}/sets",
            json={
                "exercise_id": seeded_exercises["bench_press"],
                "set_number": 1,
                "set_type": "working",
                "reps": 5,
                "weight_kg": 100,
                "logged_at": "2026-03-18T06:10:00Z",
            },
            headers=headers,
        )
        second_set = await client.post(
            f"/workout-sessions/{workout_session['id']}/sets",
            json={
                "exercise_id": seeded_exercises["bench_press"],
                "set_number": 2,
                "set_type": "working",
                "reps": 8,
                "weight_kg": 90,
                "logged_at": "2026-03-18T06:20:00Z",
            },
            headers=headers,
        )
        assert first_set.status_code == 201
        assert second_set.status_code == 201

        before_completion = await client.get("/personal-records", headers=headers)
        assert before_completion.status_code == 200
        assert before_completion.json() == []

        complete_session = await client.patch(
            f"/workout-sessions/{workout_session['id']}",
            json={
                "finished_at": "2026-03-18T07:00:00Z",
            },
            headers=headers,
        )
        assert complete_session.status_code == 200
        assert complete_session.json()["is_completed"] is True

        record_list = await client.get(
            "/personal-records",
            params={"exercise_id": seeded_exercises["bench_press"]},
            headers=headers,
        )
        assert record_list.status_code == 200
        records = record_list.json()
        assert len(records) == 6

        records_by_type = {record["record_type"]: record for record in records}
        assert set(records_by_type) == {
            "estimated_1rm",
            "max_weight",
            "5rm",
            "8rm",
            "max_reps",
            "max_volume",
        }
        assert records_by_type["estimated_1rm"]["value"] == pytest.approx(116.67, abs=0.01)
        assert records_by_type["max_weight"]["value"] == 100
        assert records_by_type["5rm"]["value"] == 100
        assert records_by_type["8rm"]["value"] == 90
        assert records_by_type["max_reps"]["value"] == 8
        assert records_by_type["max_volume"]["value"] == 1220
        assert records_by_type["max_volume"]["set_id"] is None
        assert records_by_type["max_volume"]["session_id"] == workout_session["id"]

        detail_response = await client.get(
            f"/personal-records/{records_by_type['5rm']['id']}",
            headers=headers,
        )
        assert detail_response.status_code == 200
        assert detail_response.json()["record_type"] == "5rm"

        filtered_response = await client.get(
            "/personal-records",
            params={"record_type": "max_volume"},
            headers=headers,
        )
        assert filtered_response.status_code == 200
        assert len(filtered_response.json()) == 1

        session_detail = await client.get(
            f"/workout-sessions/{workout_session['id']}",
            headers=headers,
        )
        assert session_detail.status_code == 200
        detail_sets = session_detail.json()["sets"]
        assert len(detail_sets) == 2
        assert detail_sets[0]["is_pr"] is True
        assert detail_sets[1]["is_pr"] is True

    async def test_personal_records_recalculate_for_completed_set_changes(
        self,
        client,
        seeded_exercises,
    ):
        auth_data = await register_user(client)
        headers = {"Authorization": f"Bearer {auth_data['access_token']}"}

        first_session = await client.post(
            "/workout-sessions",
            json={
                "name": "Heavy Bench",
                "started_at": "2026-03-18T06:00:00Z",
                "finished_at": "2026-03-18T07:00:00Z",
                "is_completed": True,
            },
            headers=headers,
        )
        assert first_session.status_code == 201
        first_session_id = first_session.json()["id"]

        first_heavy_set = await client.post(
            f"/workout-sessions/{first_session_id}/sets",
            json={
                "exercise_id": seeded_exercises["bench_press"],
                "set_number": 1,
                "set_type": "working",
                "reps": 5,
                "weight_kg": 100,
            },
            headers=headers,
        )
        rep_set = await client.post(
            f"/workout-sessions/{first_session_id}/sets",
            json={
                "exercise_id": seeded_exercises["bench_press"],
                "set_number": 2,
                "set_type": "working",
                "reps": 8,
                "weight_kg": 90,
            },
            headers=headers,
        )
        assert first_heavy_set.status_code == 201
        assert rep_set.status_code == 201

        second_session = await client.post(
            "/workout-sessions",
            json={
                "name": "PR Attempt",
                "started_at": "2026-03-25T06:00:00Z",
                "finished_at": "2026-03-25T07:00:00Z",
                "is_completed": True,
            },
            headers=headers,
        )
        assert second_session.status_code == 201
        second_session_id = second_session.json()["id"]

        second_heavy_set = await client.post(
            f"/workout-sessions/{second_session_id}/sets",
            json={
                "exercise_id": seeded_exercises["bench_press"],
                "set_number": 1,
                "set_type": "working",
                "reps": 5,
                "weight_kg": 110,
            },
            headers=headers,
        )
        assert second_heavy_set.status_code == 201
        heavy_set_id = second_heavy_set.json()["id"]

        updated_set = await client.patch(
            f"/workout-sessions/{second_session_id}/sets/{heavy_set_id}",
            json={"weight_kg": 112.5},
            headers=headers,
        )
        assert updated_set.status_code == 200

        after_update = await client.get(
            "/personal-records",
            params={"exercise_id": seeded_exercises["bench_press"]},
            headers=headers,
        )
        assert after_update.status_code == 200
        updated_records = {
            record["record_type"]: record
            for record in after_update.json()
        }
        assert updated_records["max_weight"]["value"] == 112.5
        assert updated_records["5rm"]["value"] == 112.5
        assert updated_records["estimated_1rm"]["value"] == pytest.approx(131.25, abs=0.01)
        assert updated_records["max_reps"]["value"] == 8
        assert updated_records["max_volume"]["value"] == 1220

        first_detail = await client.get(
            f"/workout-sessions/{first_session_id}",
            headers=headers,
        )
        second_detail = await client.get(
            f"/workout-sessions/{second_session_id}",
            headers=headers,
        )
        assert first_detail.status_code == 200
        assert second_detail.status_code == 200
        first_sets = first_detail.json()["sets"]
        second_sets = second_detail.json()["sets"]
        assert first_sets[0]["is_pr"] is False
        assert first_sets[1]["is_pr"] is True
        assert second_sets[0]["is_pr"] is True

        delete_response = await client.delete(
            f"/workout-sessions/{second_session_id}/sets/{heavy_set_id}",
            headers=headers,
        )
        assert delete_response.status_code == 204

        after_delete = await client.get(
            "/personal-records",
            params={"exercise_id": seeded_exercises["bench_press"]},
            headers=headers,
        )
        assert after_delete.status_code == 200
        reverted_records = {
            record["record_type"]: record
            for record in after_delete.json()
        }
        assert reverted_records["max_weight"]["value"] == 100
        assert reverted_records["5rm"]["value"] == 100
        assert reverted_records["estimated_1rm"]["value"] == pytest.approx(116.67, abs=0.01)

        refreshed_first_detail = await client.get(
            f"/workout-sessions/{first_session_id}",
            headers=headers,
        )
        assert refreshed_first_detail.status_code == 200
        refreshed_sets = refreshed_first_detail.json()["sets"]
        assert refreshed_sets[0]["is_pr"] is True
        assert refreshed_sets[1]["is_pr"] is True
