"""Add exercise_category and met_value to exercises, seed MET values

Revision ID: 0c3e5f1a2b4d
Revises: 7d3b1c1a0f0a
Create Date: 2026-06-24 12:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "0c3e5f1a2b4d"
down_revision: Union[str, Sequence[str], None] = "7d3b1c1a0f0a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS app_schema")

    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'exercise_category') THEN
                CREATE TYPE app_schema.exercise_category AS ENUM ('strength', 'cardio', 'flexibility', 'other');
            END IF;
        END
        $$;
    """)

    op.add_column("exercises", sa.Column("exercise_category", postgresql.ENUM("strength", "cardio", "flexibility", "other", name="exercise_category", schema="app_schema"), nullable=True), schema="app_schema")
    op.add_column("exercises", sa.Column("met_value", sa.Numeric(5, 2), nullable=True), schema="app_schema")

    op.execute("UPDATE app_schema.exercises SET exercise_category = 'strength' WHERE exercise_category IS NULL")

    MET_SEED = """
        UPDATE app_schema.exercises SET exercise_category = 'cardio', met_value = 9.8
        WHERE LOWER(name) IN ('running', 'treadmill', 'jogging');
        UPDATE app_schema.exercises SET exercise_category = 'cardio', met_value = 8.0
        WHERE LOWER(name) IN ('cycling', 'bicycle', 'bike', 'stationary bike', 'cycling moderate');
        UPDATE app_schema.exercises SET exercise_category = 'cardio', met_value = 8.0
        WHERE LOWER(name) IN ('swimming', 'freestyle', 'front crawl');
        UPDATE app_schema.exercises SET exercise_category = 'cardio', met_value = 3.5
        WHERE LOWER(name) IN ('walking', 'brisk walk', 'treadmill walk');
        UPDATE app_schema.exercises SET exercise_category = 'cardio', met_value = 8.8
        WHERE LOWER(name) IN ('jump rope', 'skipping', 'jumping rope');
        UPDATE app_schema.exercises SET exercise_category = 'cardio', met_value = 7.0
        WHERE LOWER(name) IN ('rowing', 'rowing machine', 'ergometer');
        UPDATE app_schema.exercises SET exercise_category = 'cardio', met_value = 5.0
        WHERE LOWER(name) IN ('elliptical', 'cross trainer');
        UPDATE app_schema.exercises SET exercise_category = 'cardio', met_value = 9.0
        WHERE LOWER(name) IN ('stair climber', 'stairmaster', 'step machine');
        UPDATE app_schema.exercises SET exercise_category = 'cardio', met_value = 6.0
        WHERE LOWER(name) IN ('hiking', 'hill walking');
        UPDATE app_schema.exercises SET exercise_category = 'cardio', met_value = 8.0
        WHERE LOWER(name) IN ('hiit', 'high intensity interval training', 'interval training');
        UPDATE app_schema.exercises SET exercise_category = 'cardio', met_value = 7.0
        WHERE LOWER(name) IN ('boxing', 'kickboxing', 'punching bag');
    """
    op.execute(MET_SEED)

    op.execute("""
        UPDATE app_schema.exercises SET exercise_category = 'flexibility'
        WHERE LOWER(name) IN (
            'stretching', 'yoga', 'pilates', 'foam rolling', 'mobility',
            'static stretch', 'dynamic stretch', 'hatha yoga', 'vinyasa'
        )
    """)


def downgrade() -> None:
    op.drop_column("exercises", "met_value", schema="app_schema")
    op.drop_column("exercises", "exercise_category", schema="app_schema")
    op.execute("DROP TYPE IF EXISTS app_schema.exercise_category")
