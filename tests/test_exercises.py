from sqlalchemy.orm import Session
import pytest

from app.models.exercise import Exercise, ExerciseInstruction, ExerciseSecondaryMuscle

pytestmark = pytest.mark.asyncio


@pytest.fixture
def seeded_exercises(client, test_db):
    push_up_id = "push-up"
    pull_up_id = "pull-up"
    curl_id = "curl"

    with Session(test_db) as session:
        exercise_one = Exercise(
            id=push_up_id,
            name="Push Up",
            body_part="chest",
            equipment="body weight",
            gif_url="https://example.com/push-up.gif",
            target="pectorals",
            instructions=[
                ExerciseInstruction(step_number=1, instruction="Start in a plank."),
                ExerciseInstruction(step_number=2, instruction="Lower your chest."),
            ],
            secondary_muscles=[
                ExerciseSecondaryMuscle(muscle="triceps"),
                ExerciseSecondaryMuscle(muscle="shoulders"),
            ],
        )
        exercise_two = Exercise(
            id=pull_up_id,
            name="Pull Up",
            body_part="back",
            equipment="body weight",
            gif_url="https://example.com/pull-up.gif",
            target="lats",
            instructions=[
                ExerciseInstruction(step_number=1, instruction="Hang from the bar."),
            ],
            secondary_muscles=[
                ExerciseSecondaryMuscle(muscle="biceps"),
            ],
        )
        exercise_three = Exercise(
            id=curl_id,
            name="Dumbbell Curl",
            body_part="upper arms",
            equipment="dumbbell",
            gif_url="https://example.com/curl.gif",
            target="biceps",
        )

        session.add_all([exercise_one, exercise_two, exercise_three])
        session.commit()

    return {
        "push_up": push_up_id,
        "pull_up": pull_up_id,
        "curl": curl_id,
    }


class TestExerciseEndpoints:
    async def test_list_exercises_returns_paginated_catalog(self, client, seeded_exercises):
        response = await client.get("/exercises", params={"limit": 2})

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 3
        assert data["limit"] == 2
        assert data["offset"] == 0
        assert [item["name"] for item in data["items"]] == ["Dumbbell Curl", "Pull Up"]

    async def test_list_exercises_supports_search_and_filters(self, client, seeded_exercises):
        response = await client.get(
            "/exercises",
            params={
                "q": "pull",
                "body_part": "BACK",
                "equipment": "body weight",
                "target": "LATS",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert len(data["items"]) == 1
        assert data["items"][0]["id"] == seeded_exercises["pull_up"]

    async def test_get_exercise_returns_nested_details(self, client, seeded_exercises):
        response = await client.get(f"/exercises/{seeded_exercises['push_up']}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == seeded_exercises["push_up"]
        assert [item["step_number"] for item in data["instructions"]] == [1, 2]
        assert [item["muscle"] for item in data["secondary_muscles"]] == [
            "shoulders",
            "triceps",
        ]

    async def test_get_exercise_filters_returns_distinct_values(self, client, seeded_exercises):
        response = await client.get("/exercises/filters")

        assert response.status_code == 200
        data = response.json()
        assert data["body_parts"] == ["back", "chest", "upper arms"]
        assert data["equipment"] == ["body weight", "dumbbell"]
        assert data["targets"] == ["biceps", "lats", "pectorals"]

    async def test_get_exercise_returns_404_for_unknown_id(self, client, seeded_exercises):
        response = await client.get("/exercises/unknown")

        assert response.status_code == 404
        assert response.json()["detail"] == "Exercise not found"
