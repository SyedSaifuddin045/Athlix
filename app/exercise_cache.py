from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.exercise import Exercise
from app.schemas.exercise_schema import ExerciseResponse, ExerciseDetailResponse

CANONICAL_CARDIO_EXERCISES: dict[str, dict[str, Any]] = {
    "cardio_run": {
        "name": "Running (Outdoor)",
        "body_part": "cardio",
        "equipment": "body weight",
        "target": "cardiovascular",
        "exercise_category": "cardio",
        "met_value": 9.8,
        "instructions": [
            "Warm up with 5–10 minutes of light jogging or dynamic stretches.",
            "Maintain an upright posture with your head up, shoulders relaxed, and arms at a 90-degree angle.",
            "Land mid-foot and roll through to the toe with each stride.",
            "Breathe rhythmically — inhale for 3 steps, exhale for 2 steps.",
            "Cool down with 5 minutes of walking followed by static stretches.",
        ],
    },
    "cardio_walk": {
        "name": "Walking",
        "body_part": "cardio",
        "equipment": "body weight",
        "target": "cardiovascular",
        "exercise_category": "cardio",
        "met_value": 3.5,
        "instructions": [
            "Stand tall with your head up, shoulders back, and core engaged.",
            "Swing your arms naturally opposite to your legs.",
            "Land heel-first and roll through to the toe.",
            "Maintain a steady pace where you can still hold a conversation.",
            "Gradually increase duration or intensity for continued benefit.",
        ],
    },
    "cardio_cycle": {
        "name": "Cycling (Outdoor)",
        "body_part": "cardio",
        "equipment": "body weight",
        "target": "cardiovascular",
        "exercise_category": "cardio",
        "met_value": 8.0,
        "instructions": [
            "Adjust your saddle height so your leg is almost fully extended at the bottom of the pedal stroke.",
            "Wear a helmet and ensure your bike is in good working condition.",
            "Start in a low gear and gradually build up resistance.",
            "Maintain a cadence of 70–90 RPM for optimal efficiency.",
            "Use your core to stabilise your upper body and reduce fatigue.",
        ],
    },
    "cardio_swim": {
        "name": "Swimming",
        "body_part": "cardio",
        "equipment": "body weight",
        "target": "cardiovascular",
        "exercise_category": "cardio",
        "met_value": 8.0,
        "instructions": [
            "Begin with a 5-minute warm-up of easy laps or poolside stretching.",
            "Focus on smooth, rhythmic breathing — exhale underwater, inhale when turning your head.",
            "Keep your body horizontal and streamlined with a gentle core engagement.",
            "Use long, deliberate strokes and avoid crossing your hands past the centre line.",
            "Cool down with a few slow laps and light stretching.",
        ],
    },
    "cardio_hike": {
        "name": "Hiking",
        "body_part": "cardio",
        "equipment": "body weight",
        "target": "cardiovascular",
        "exercise_category": "cardio",
        "met_value": 6.0,
        "instructions": [
            "Wear supportive footwear and carry plenty of water and snacks.",
            "Start at a comfortable pace and use trekking poles on steep terrain if needed.",
            "Take shorter steps on inclines and lean slightly forward from the ankles.",
            "Descend carefully with slightly bent knees to reduce joint impact.",
            "Take breaks every 20–30 minutes to hydrate and assess the trail ahead.",
        ],
    },
    "cardio_row": {
        "name": "Rowing Machine",
        "body_part": "cardio",
        "equipment": "rowing machine",
        "target": "cardiovascular",
        "exercise_category": "cardio",
        "met_value": 7.0,
        "instructions": [
            "Start with your shins vertical, arms straight, and back tall (the catch position).",
            "Drive through your legs first, then hinge your torso back, and finally pull the handle to your lower ribs.",
            "Reverse the motion: extend your arms, hinge forward at the hips, then bend your knees.",
            "Maintain a 1:2 ratio — one count on the drive, two counts on the recovery.",
            "Set the damper to 4–6 for an all-round workout; adjust based on feel.",
        ],
    },
    "cardio_elliptical": {
        "name": "Elliptical Trainer",
        "body_part": "cardio",
        "equipment": "elliptical machine",
        "target": "cardiovascular",
        "exercise_category": "cardio",
        "met_value": 5.0,
        "instructions": [
            "Step onto the machine and select a program or manual mode.",
            "Stand upright with your core engaged — do not lean on the handles.",
            "Pedal forward in a smooth, continuous motion with your heels flat.",
            "Increase resistance gradually rather than relying on speed alone.",
            "Cool down with 3–5 minutes of low-resistance pedalling.",
        ],
    },
    "cardio_stair": {
        "name": "Stair Climber",
        "body_part": "cardio",
        "equipment": "stepmill machine",
        "target": "cardiovascular",
        "exercise_category": "cardio",
        "met_value": 9.0,
        "instructions": [
            "Step onto the machine and select your desired speed or program.",
            "Stand upright and hold the handrails lightly for balance — avoid putting weight on them.",
            "Take full steps rather than half-steps to engage your glutes fully.",
            "Keep your pace steady and breathe deeply throughout the session.",
            "Step off one foot at a time when finishing, and allow the machine to stop fully.",
        ],
    },
    "cardio_treadmill": {
        "name": "Treadmill (Running)",
        "body_part": "cardio",
        "equipment": "treadmill",
        "target": "cardiovascular",
        "exercise_category": "cardio",
        "met_value": 9.8,
        "instructions": [
            "Start at a slow walking pace to warm up for 3–5 minutes before increasing speed.",
            "Maintain an upright posture with your gaze forward — avoid looking down at your feet.",
            "Land mid-foot with a quick, light cadence to minimise impact.",
            "Use the safety clip in case of an emergency.",
            "Cool down by gradually reducing speed to a walk for 3–5 minutes.",
        ],
    },
    "cardio_bike": {
        "name": "Stationary Bike",
        "body_part": "cardio",
        "equipment": "stationary bike",
        "target": "cardiovascular",
        "exercise_category": "cardio",
        "met_value": 8.0,
        "instructions": [
            "Adjust the seat height so your knee is slightly bent at the bottom of the pedal stroke.",
            "Start pedalling at a low resistance to warm up for 3–5 minutes.",
            "Maintain a cadence of 70–90 RPM with smooth, circular pedal strokes.",
            "Increase resistance in small increments for a progressive challenge.",
            "Cool down with 3–5 minutes of easy pedalling at low resistance.",
        ],
    },
}


class ExerciseCache:
    _all_exercises: list[ExerciseResponse] | None = None
    _exercise_map: dict[str, ExerciseResponse] | None = None
    _detail_map: dict[str, ExerciseDetailResponse] | None = None

    @classmethod
    def load(cls, db: Session) -> None:
        exercises = db.execute(
            select(Exercise).order_by(Exercise.name.asc(), Exercise.id.asc())
        ).scalars().all()

        cls._all_exercises = [ExerciseResponse.model_validate(e) for e in exercises]
        cls._exercise_map = {e.id: e for e in cls._all_exercises}

        details = db.execute(
            select(Exercise)
            .options(
                selectinload(Exercise.instructions),
                selectinload(Exercise.secondary_muscles),
            )
            .order_by(Exercise.name.asc(), Exercise.id.asc())
        ).scalars().all()

        cls._detail_map = {
            d.id: ExerciseDetailResponse.model_validate(d) for d in details
        }

    @classmethod
    def _ensure_loaded(cls) -> None:
        if cls._all_exercises is not None:
            return
        from app.core.database import SessionLocal

        db = SessionLocal()
        try:
            cls.load(db)
        finally:
            db.close()

    @classmethod
    def all(cls) -> list[ExerciseResponse]:
        cls._ensure_loaded()
        return cls._all_exercises  # type: ignore[return-value]

    @classmethod
    def get(cls, exercise_id: str) -> ExerciseResponse | None:
        cls._ensure_loaded()
        if cls._exercise_map is None:
            return None
        return cls._exercise_map.get(exercise_id)

    @classmethod
    def get_detail(cls, exercise_id: str) -> ExerciseDetailResponse | None:
        cls._ensure_loaded()
        if cls._detail_map is None:
            return None
        return cls._detail_map.get(exercise_id)

    @classmethod
    def is_loaded(cls) -> bool:
        return cls._all_exercises is not None
