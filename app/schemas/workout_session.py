from datetime import datetime

from .base_schema import BaseSchema
from .exercise_set import ExerciseSetResponse


class WorkoutSessionCreate(BaseSchema):
    template_id: int | None = None
    mesocycle_id: int | None = None
    name: str | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None
    perceived_exertion: int | None = None
    mood: str | None = None
    location: str | None = None
    notes: str | None = None
    is_completed: bool = False


class WorkoutSessionUpdate(BaseSchema):
    template_id: int | None = None
    mesocycle_id: int | None = None
    name: str | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None
    perceived_exertion: int | None = None
    mood: str | None = None
    location: str | None = None
    notes: str | None = None
    is_completed: bool | None = None


class WorkoutSessionResponse(BaseSchema):
    id: int
    user_id: int
    template_id: int | None
    mesocycle_id: int | None
    name: str | None
    started_at: datetime
    finished_at: datetime | None
    perceived_exertion: int | None
    mood: str | None
    location: str | None
    notes: str | None
    is_completed: bool


class WorkoutSessionDetailResponse(WorkoutSessionResponse):
    sets: list[ExerciseSetResponse]
