from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.exercise import Exercise
from app.schemas.exercise_schema import ExerciseResponse, ExerciseDetailResponse

CANONICAL_CARDIO_EXERCISES: dict[str, dict[str, str | float]] = {
    "cardio_run": {
        "name": "Running (Outdoor)",
        "body_part": "cardio",
        "equipment": "body weight",
        "target": "cardiovascular",
        "exercise_category": "cardio",
        "met_value": 9.8,
    },
    "cardio_walk": {
        "name": "Walking",
        "body_part": "cardio",
        "equipment": "body weight",
        "target": "cardiovascular",
        "exercise_category": "cardio",
        "met_value": 3.5,
    },
    "cardio_cycle": {
        "name": "Cycling (Outdoor)",
        "body_part": "cardio",
        "equipment": "body weight",
        "target": "cardiovascular",
        "exercise_category": "cardio",
        "met_value": 8.0,
    },
    "cardio_swim": {
        "name": "Swimming",
        "body_part": "cardio",
        "equipment": "body weight",
        "target": "cardiovascular",
        "exercise_category": "cardio",
        "met_value": 8.0,
    },
    "cardio_hike": {
        "name": "Hiking",
        "body_part": "cardio",
        "equipment": "body weight",
        "target": "cardiovascular",
        "exercise_category": "cardio",
        "met_value": 6.0,
    },
    "cardio_row": {
        "name": "Rowing Machine",
        "body_part": "cardio",
        "equipment": "rowing machine",
        "target": "cardiovascular",
        "exercise_category": "cardio",
        "met_value": 7.0,
    },
    "cardio_elliptical": {
        "name": "Elliptical Trainer",
        "body_part": "cardio",
        "equipment": "elliptical machine",
        "target": "cardiovascular",
        "exercise_category": "cardio",
        "met_value": 5.0,
    },
    "cardio_stair": {
        "name": "Stair Climber",
        "body_part": "cardio",
        "equipment": "stepmill machine",
        "target": "cardiovascular",
        "exercise_category": "cardio",
        "met_value": 9.0,
    },
    "cardio_treadmill": {
        "name": "Treadmill (Running)",
        "body_part": "cardio",
        "equipment": "treadmill",
        "target": "cardiovascular",
        "exercise_category": "cardio",
        "met_value": 9.8,
    },
    "cardio_bike": {
        "name": "Stationary Bike",
        "body_part": "cardio",
        "equipment": "stationary bike",
        "target": "cardiovascular",
        "exercise_category": "cardio",
        "met_value": 8.0,
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
