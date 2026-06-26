"""seed canonical cardio exercises

Revision ID: c8d9e0f1a2b3
Revises: b9b3ac1ccd42
Create Date: 2026-06-25
"""
from alembic import op
from sqlalchemy import text

revision = "c8d9e0f1a2b3"
down_revision = "b9b3ac1ccd42"
branch_labels = None
depends_on = None


CARDIO_EXERCISES = [
    {
        "id": "cardio_run",
        "name": "Running (Outdoor)",
        "body_part": "cardio",
        "equipment": "body weight",
        "target": "cardiovascular",
        "exercise_category": "cardio",
        "met_value": 9.8,
    },
    {
        "id": "cardio_walk",
        "name": "Walking",
        "body_part": "cardio",
        "equipment": "body weight",
        "target": "cardiovascular",
        "exercise_category": "cardio",
        "met_value": 3.5,
    },
    {
        "id": "cardio_cycle",
        "name": "Cycling (Outdoor)",
        "body_part": "cardio",
        "equipment": "body weight",
        "target": "cardiovascular",
        "exercise_category": "cardio",
        "met_value": 8.0,
    },
    {
        "id": "cardio_swim",
        "name": "Swimming",
        "body_part": "cardio",
        "equipment": "body weight",
        "target": "cardiovascular",
        "exercise_category": "cardio",
        "met_value": 8.0,
    },
    {
        "id": "cardio_hike",
        "name": "Hiking",
        "body_part": "cardio",
        "equipment": "body weight",
        "target": "cardiovascular",
        "exercise_category": "cardio",
        "met_value": 6.0,
    },
    {
        "id": "cardio_row",
        "name": "Rowing Machine",
        "body_part": "cardio",
        "equipment": "rowing machine",
        "target": "cardiovascular",
        "exercise_category": "cardio",
        "met_value": 7.0,
    },
    {
        "id": "cardio_elliptical",
        "name": "Elliptical Trainer",
        "body_part": "cardio",
        "equipment": "elliptical machine",
        "target": "cardiovascular",
        "exercise_category": "cardio",
        "met_value": 5.0,
    },
    {
        "id": "cardio_stair",
        "name": "Stair Climber",
        "body_part": "cardio",
        "equipment": "stepmill machine",
        "target": "cardiovascular",
        "exercise_category": "cardio",
        "met_value": 9.0,
    },
    {
        "id": "cardio_treadmill",
        "name": "Treadmill (Running)",
        "body_part": "cardio",
        "equipment": "treadmill",
        "target": "cardiovascular",
        "exercise_category": "cardio",
        "met_value": 9.8,
    },
    {
        "id": "cardio_bike",
        "name": "Stationary Bike",
        "body_part": "cardio",
        "equipment": "stationary bike",
        "target": "cardiovascular",
        "exercise_category": "cardio",
        "met_value": 8.0,
    },
]


def upgrade():
    conn = op.get_bind()
    for ex in CARDIO_EXERCISES:
        conn.execute(
            text("""
                INSERT INTO app_schema.exercises
                    (id, name, body_part, equipment, target,
                     exercise_category, met_value)
                VALUES
                    (:id, :name, :body_part, :equipment, :target,
                     :exercise_category, :met_value)
                ON CONFLICT (id) DO NOTHING
            """),
            {
                "id": ex["id"],
                "name": ex["name"],
                "body_part": ex["body_part"],
                "equipment": ex["equipment"],
                "target": ex["target"],
                "exercise_category": ex["exercise_category"],
                "met_value": ex["met_value"],
            },
        )


def downgrade():
    conn = op.get_bind()
    ids = [ex["id"] for ex in CARDIO_EXERCISES]
    for eid in ids:
        conn.execute(
            text("DELETE FROM app_schema.exercises WHERE id = :id"),
            {"id": eid},
        )
