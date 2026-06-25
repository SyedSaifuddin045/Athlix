"""Reseed exercise categories with keyword matching

Revision ID: b9b3ac1ccd42
Revises: 0c3e5f1a2b4d
Create Date: 2026-06-25 22:24:18.610072

"""

from typing import Sequence, Union

from alembic import op


revision: str = "b9b3ac1ccd42"
down_revision: Union[str, Sequence[str], None] = "0c3e5f1a2b4d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

EX = "app_schema.exercises"


def upgrade() -> None:
    op.execute(f"UPDATE {EX} SET exercise_category = 'strength', met_value = NULL")

    op.execute(f"""
        UPDATE {EX} SET exercise_category = 'cardio', met_value = 8.0
        WHERE LOWER(name) ~ '^(run|jog|cycle|bike|swim|walk|ski\\ |skate|hiit|burpee|mountain\\ climber|astride\\ jump|scissor\\ jump|jack\\ jump|star\\ jump|semi\\ squat\\ jump|forward\\ jump|backward\\ jump|box\\ jump|sprint|cardio|kettlebell\\ swing|short\\ stride|wheel\\ run|rope\\ climb|push\\ to\\ run|hands\\ bike|air\\ bike|elliptical|stairmaster|stair\\ climb|step\\ mill)'
        OR LOWER(name) IN ('run (equipment)','walking lunge','walking high knees lunge','walking on incline treadmill','walking on stepmill','walk elliptical cross trainer','cycle cross trainer','stationary bike run v. 3','stationary bike walk','kettlebell swing','jump rope','swimmer kicks v. 2 (male)','skater hops','ski ergometer','ski step','burpee','mountain climber')
    """)

    op.execute(f"""
        UPDATE {EX} SET exercise_category = 'flexibility', met_value = 2.5
        WHERE LOWER(name) ~ '(stretch|yoga)'
        AND LOWER(name) NOT IN ('standing hamstring and calf stretch with strap')
    """)

    op.execute(f"""
        UPDATE {EX} SET met_value = 9.8
        WHERE exercise_category = 'cardio' AND LOWER(name) ~ '^(run|jog)'
    """)
    op.execute(f"""
        UPDATE {EX} SET met_value = 8.0
        WHERE exercise_category = 'cardio' AND LOWER(name) ~ '^(cycle|bike)'
    """)
    op.execute(f"""
        UPDATE {EX} SET met_value = 6.0
        WHERE exercise_category = 'cardio' AND LOWER(name) ~ '^(walk|elliptical|stair)'
    """)
    op.execute(f"""
        UPDATE {EX} SET met_value = 10.0
        WHERE exercise_category = 'cardio' AND LOWER(name) ~ '(jump\\ rope|burpee|hiit)'
    """)


def downgrade() -> None:
    op.execute(f"UPDATE {EX} SET exercise_category = 'strength', met_value = NULL")
