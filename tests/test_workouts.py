from datetime import date, datetime, timezone

import pytest
from sqlalchemy.orm import Session

from app.models.exercise import Exercise
from app.models.mesocycle import Mesocycle

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
                    id="push-up",
                    name="Push Up",
                    body_part="chest",
                    equipment="body weight",
                    gif_url="https://example.com/push-up.gif",
                    target="pectorals",
                ),
                Exercise(
                    id="row",
                    name="Cable Row",
                    body_part="back",
                    equipment="cable",
                    gif_url="https://example.com/row.gif",
                    target="lats",
                ),
            ]
        )
        session.commit()

    return {
        "push_up": "push-up",
        "row": "row",
    }


def create_mesocycle(test_db, user_id: int) -> int:
    with Session(test_db) as session:
        mesocycle = Mesocycle(
            user_id=user_id,
            name="Hypertrophy Block",
            goal="hypertrophy",
            started_on=date(2026, 3, 1),
            ended_on=date(2026, 4, 12),
            weeks=6,
            notes="Spring block",
            created_at=datetime(2026, 3, 1, tzinfo=timezone.utc),
        )
        session.add(mesocycle)
        session.commit()
        session.refresh(mesocycle)
        return mesocycle.id


class TestWorkoutTemplateEndpoints:
    async def test_workout_template_crud_flow(self, client, seeded_exercises):
        auth_data = await register_user(client)
        headers = {"Authorization": f"Bearer {auth_data['access_token']}"}

        create_response = await client.post(
            "/workout-templates",
            json={
                "name": "Push Day A",
                "description": "Primary upper push session",
                "is_public": False,
            },
            headers=headers,
        )

        assert create_response.status_code == 201
        template = create_response.json()
        assert template["name"] == "Push Day A"

        list_response = await client.get("/workout-templates", headers=headers)
        assert list_response.status_code == 200
        assert len(list_response.json()) == 1

        update_response = await client.patch(
            f"/workout-templates/{template['id']}",
            json={
                "description": "Updated description",
                "is_public": True,
            },
            headers=headers,
        )
        assert update_response.status_code == 200
        assert update_response.json()["is_public"] is True

        create_template_exercise = await client.post(
            f"/workout-templates/{template['id']}/exercises",
            json={
                "exercise_id": seeded_exercises["push_up"],
                "order_index": 1,
                "target_sets": 4,
                "target_reps": 10,
                "target_rpe": 8.5,
                "rest_seconds": 120,
                "notes": "Controlled tempo",
            },
            headers=headers,
        )
        assert create_template_exercise.status_code == 201
        template_exercise = create_template_exercise.json()

        detail_response = await client.get(
            f"/workout-templates/{template['id']}",
            headers=headers,
        )
        assert detail_response.status_code == 200
        detail = detail_response.json()
        assert len(detail["exercises"]) == 1
        assert detail["exercises"][0]["exercise_id"] == seeded_exercises["push_up"]

        update_template_exercise = await client.patch(
            f"/workout-templates/{template['id']}/exercises/{template_exercise['id']}",
            json={
                "exercise_id": seeded_exercises["row"],
                "order_index": 2,
                "target_sets": 3,
            },
            headers=headers,
        )
        assert update_template_exercise.status_code == 200
        updated_template_exercise = update_template_exercise.json()
        assert updated_template_exercise["exercise_id"] == seeded_exercises["row"]
        assert updated_template_exercise["order_index"] == 2

        delete_template_exercise = await client.delete(
            f"/workout-templates/{template['id']}/exercises/{template_exercise['id']}",
            headers=headers,
        )
        assert delete_template_exercise.status_code == 204

        delete_template = await client.delete(
            f"/workout-templates/{template['id']}",
            headers=headers,
        )
        assert delete_template.status_code == 204

        missing_response = await client.get(
            f"/workout-templates/{template['id']}",
            headers=headers,
        )
        assert missing_response.status_code == 404
        assert missing_response.json()["detail"] == "Workout template not found"

    async def test_workout_template_rejects_unknown_exercise(self, client, seeded_exercises):
        auth_data = await register_user(client)
        headers = {"Authorization": f"Bearer {auth_data['access_token']}"}

        template_response = await client.post(
            "/workout-templates",
            json={"name": "Template", "description": None, "is_public": False},
            headers=headers,
        )
        template_id = template_response.json()["id"]

        response = await client.post(
            f"/workout-templates/{template_id}/exercises",
            json={
                "exercise_id": "missing",
                "order_index": 1,
            },
            headers=headers,
        )

        assert response.status_code == 404
        assert response.json()["detail"] == "Exercise not found"


class TestWorkoutSessionEndpoints:
    async def test_workout_session_and_set_crud_flow(self, client, test_db, seeded_exercises):
        auth_data = await register_user(client)
        headers = {"Authorization": f"Bearer {auth_data['access_token']}"}
        mesocycle_id = create_mesocycle(test_db, auth_data["user"]["id"])

        template_response = await client.post(
            "/workout-templates",
            json={
                "name": "Pull Day A",
                "description": "Back emphasis",
                "is_public": False,
            },
            headers=headers,
        )
        assert template_response.status_code == 201
        template_id = template_response.json()["id"]

        create_response = await client.post(
            "/workout-sessions",
            json={
                "template_id": template_id,
                "mesocycle_id": mesocycle_id,
                "name": "Wednesday Pull",
                "started_at": "2026-03-18T06:30:00Z",
                "notes": "Felt strong",
            },
            headers=headers,
        )
        assert create_response.status_code == 201
        workout_session = create_response.json()
        assert workout_session["template_id"] == template_id
        assert workout_session["mesocycle_id"] == mesocycle_id
        assert workout_session["is_completed"] is False

        list_response = await client.get("/workout-sessions", headers=headers)
        assert list_response.status_code == 200
        assert len(list_response.json()) == 1

        update_response = await client.patch(
            f"/workout-sessions/{workout_session['id']}",
            json={
                "finished_at": "2026-03-18T07:40:00Z",
                "perceived_exertion": 8,
                "location": "gym",
            },
            headers=headers,
        )
        assert update_response.status_code == 200
        updated_session = update_response.json()
        assert updated_session["is_completed"] is True
        assert updated_session["perceived_exertion"] == 8

        create_set_response = await client.post(
            f"/workout-sessions/{workout_session['id']}/sets",
            json={
                "exercise_id": seeded_exercises["row"],
                "set_number": 1,
                "set_type": "working",
                "reps": 12,
                "weight_kg": 55,
                "rpe": 8,
                "notes": "Smooth reps",
                "logged_at": "2026-03-18T06:45:00Z",
            },
            headers=headers,
        )
        assert create_set_response.status_code == 201
        exercise_set = create_set_response.json()
        assert exercise_set["exercise_id"] == seeded_exercises["row"]

        detail_response = await client.get(
            f"/workout-sessions/{workout_session['id']}",
            headers=headers,
        )
        assert detail_response.status_code == 200
        detail = detail_response.json()
        assert len(detail["sets"]) == 1
        assert detail["sets"][0]["id"] == exercise_set["id"]

        update_set_response = await client.patch(
            f"/workout-sessions/{workout_session['id']}/sets/{exercise_set['id']}",
            json={
                "reps": 10,
                "weight_kg": 60,
                "is_pr": True,
            },
            headers=headers,
        )
        assert update_set_response.status_code == 200
        updated_set = update_set_response.json()
        assert updated_set["weight_kg"] == 60
        assert updated_set["is_pr"] is True

        delete_set_response = await client.delete(
            f"/workout-sessions/{workout_session['id']}/sets/{exercise_set['id']}",
            headers=headers,
        )
        assert delete_set_response.status_code == 204

        missing_set_response = await client.get(
            f"/workout-sessions/{workout_session['id']}/sets/{exercise_set['id']}",
            headers=headers,
        )
        assert missing_set_response.status_code == 404
        assert missing_set_response.json()["detail"] == "Exercise set not found"

    async def test_workout_session_rejects_foreign_template_reference(
        self,
        client,
        seeded_exercises,
    ):
        first_user = await register_user(client)
        second_user = await register_user(
            client,
            username="athlete_two",
            email="athlete.two@example.com",
        )

        first_headers = {"Authorization": f"Bearer {first_user['access_token']}"}
        second_headers = {"Authorization": f"Bearer {second_user['access_token']}"}

        template_response = await client.post(
            "/workout-templates",
            json={
                "name": "Private Template",
                "description": "Owned by first user",
                "is_public": False,
            },
            headers=first_headers,
        )
        assert template_response.status_code == 201
        foreign_template_id = template_response.json()["id"]

        response = await client.post(
            "/workout-sessions",
            json={
                "template_id": foreign_template_id,
                "name": "Should fail",
            },
            headers=second_headers,
        )

        assert response.status_code == 404
        assert response.json()["detail"] == "Workout template not found"
