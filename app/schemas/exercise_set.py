from datetime import datetime

from .base_schema import BaseSchema


class ExerciseSetCreate(BaseSchema):
    exercise_id: str
    set_number: int
    set_type: str
    reps: int | None = None
    weight_kg: float | None = None
    duration_sec: int | None = None
    distance_m: float | None = None
    rpe: float | None = None
    is_pr: bool = False
    notes: str | None = None
    logged_at: datetime | None = None


class ExerciseSetUpdate(BaseSchema):
    exercise_id: str | None = None
    set_number: int | None = None
    set_type: str | None = None
    reps: int | None = None
    weight_kg: float | None = None
    duration_sec: int | None = None
    distance_m: float | None = None
    rpe: float | None = None
    is_pr: bool | None = None
    notes: str | None = None
    logged_at: datetime | None = None


class ExerciseSetResponse(BaseSchema):
    id: int
    session_id: int
    exercise_id: str
    set_number: int
    set_type: str
    reps: int | None
    weight_kg: float | None
    duration_sec: int | None
    distance_m: float | None
    rpe: float | None
    is_pr: bool
    notes: str | None
    logged_at: datetime
