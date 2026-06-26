"""backfill cardio exercise instructions
Revision ID: f2dc2ae8aa2b
Revises: 18af4fbd352f
"""
from typing import Sequence, Union

from alembic import op
from sqlalchemy import text

revision: str = 'f2dc2ae8aa2b'
down_revision: Union[str, Sequence[str], None] = '18af4fbd352f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

INSTRUCTIONS_MAP = {
    "cardio_run": [
        "Warm up with 5-10 minutes of light jogging or dynamic stretches.",
        "Maintain an upright posture with your head up, shoulders relaxed, and arms at a 90-degree angle.",
        "Land mid-foot and roll through to the toe with each stride.",
        "Breathe rhythmically - inhale for 3 steps, exhale for 2 steps.",
        "Cool down with 5 minutes of walking followed by static stretches.",
    ],
    "cardio_walk": [
        "Stand tall with your head up, shoulders back, and core engaged.",
        "Swing your arms naturally opposite to your legs.",
        "Land heel-first and roll through to the toe.",
        "Maintain a steady pace where you can still hold a conversation.",
        "Gradually increase duration or intensity for continued benefit.",
    ],
    "cardio_cycle": [
        "Adjust your saddle height so your leg is almost fully extended at the bottom of the pedal stroke.",
        "Wear a helmet and ensure your bike is in good working condition.",
        "Start in a low gear and gradually build up resistance.",
        "Maintain a cadence of 70-90 RPM for optimal efficiency.",
        "Use your core to stabilise your upper body and reduce fatigue.",
    ],
    "cardio_swim": [
        "Begin with a 5-minute warm-up of easy laps or poolside stretching.",
        "Focus on smooth, rhythmic breathing - exhale underwater, inhale when turning your head.",
        "Keep your body horizontal and streamlined with a gentle core engagement.",
        "Use long, deliberate strokes and avoid crossing your hands past the centre line.",
        "Cool down with a few slow laps and light stretching.",
    ],
    "cardio_hike": [
        "Wear supportive footwear and carry plenty of water and snacks.",
        "Start at a comfortable pace and use trekking poles on steep terrain if needed.",
        "Take shorter steps on inclines and lean slightly forward from the ankles.",
        "Descend carefully with slightly bent knees to reduce joint impact.",
        "Take breaks every 20-30 minutes to hydrate and assess the trail ahead.",
    ],
    "cardio_row": [
        "Start with your shins vertical, arms straight, and back tall (the catch position).",
        "Drive through your legs first, then hinge your torso back, and finally pull the handle to your lower ribs.",
        "Reverse the motion: extend your arms, hinge forward at the hips, then bend your knees.",
        "Maintain a 1:2 ratio - one count on the drive, two counts on the recovery.",
        "Set the damper to 4-6 for an all-round workout; adjust based on feel.",
    ],
    "cardio_elliptical": [
        "Step onto the machine and select a program or manual mode.",
        "Stand upright with your core engaged - do not lean on the handles.",
        "Pedal forward in a smooth, continuous motion with your heels flat.",
        "Increase resistance gradually rather than relying on speed alone.",
        "Cool down with 3-5 minutes of low-resistance pedalling.",
    ],
    "cardio_stair": [
        "Step onto the machine and select your desired speed or program.",
        "Stand upright and hold the handrails lightly for balance - avoid putting weight on them.",
        "Take full steps rather than half-steps to engage your glutes fully.",
        "Keep your pace steady and breathe deeply throughout the session.",
        "Step off one foot at a time when finishing, and allow the machine to stop fully.",
    ],
    "cardio_treadmill": [
        "Start at a slow walking pace to warm up for 3-5 minutes before increasing speed.",
        "Maintain an upright posture with your gaze forward - avoid looking down at your feet.",
        "Land mid-foot with a quick, light cadence to minimise impact.",
        "Use the safety clip in case of an emergency.",
        "Cool down by gradually reducing speed to a walk for 3-5 minutes.",
    ],
    "cardio_bike": [
        "Adjust the seat height so your knee is slightly bent at the bottom of the pedal stroke.",
        "Start pedalling at a low resistance to warm up for 3-5 minutes.",
        "Maintain a cadence of 70-90 RPM with smooth, circular pedal strokes.",
        "Increase resistance in small increments for a progressive challenge.",
        "Cool down with 3-5 minutes of easy pedalling at low resistance.",
    ],
}


def upgrade():
    conn = op.get_bind()
    for exercise_id, steps in INSTRUCTIONS_MAP.items():
        existing = conn.execute(
            text("SELECT COUNT(*) FROM app_schema.exercise_instructions WHERE exercise_id = :eid"),
            {"eid": exercise_id},
        ).scalar()
        if existing and existing > 0:
            continue
        for i, instruction in enumerate(steps):
            conn.execute(
                text("""
                    INSERT INTO app_schema.exercise_instructions
                        (exercise_id, step_number, instruction)
                    VALUES (:eid, :step, :instr)
                    ON CONFLICT DO NOTHING
                """),
                {"eid": exercise_id, "step": i + 1, "instr": instruction},
            )


def downgrade():
    conn = op.get_bind()
    for exercise_id in INSTRUCTIONS_MAP:
        conn.execute(
            text("DELETE FROM app_schema.exercise_instructions WHERE exercise_id = :eid"),
            {"eid": exercise_id},
        )
