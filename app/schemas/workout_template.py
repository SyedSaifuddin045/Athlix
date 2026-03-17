from datetime import datetime
from .base_schema import BaseSchema


class WorkoutTemplateCreate(BaseSchema):
    name: str
    description: str | None = None
    is_public: bool = False


class WorkoutTemplateResponse(BaseSchema):
    id: int
    user_id: int
    name: str
    description: str | None
    is_public: bool
    created_at: datetime
    updated_at: datetime

class WorkoutTemplateExerciseCreate(BaseSchema):
    exercise_id: str
    order_index: int
    target_sets: int | None = None
    target_reps: int | None = None
    target_rpe: float | None = None
    rest_seconds: int | None = None
    notes: str | None = None


class WorkoutTemplateExerciseResponse(BaseSchema):
    id: int
    template_id: int
    exercise_id: str
    order_index: int
    target_sets: int | None
    target_reps: int | None
    target_rpe: float | None
    rest_seconds: int | None
    notes: str | None