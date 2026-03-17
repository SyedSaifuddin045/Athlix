from datetime import datetime
from .base_schema import BaseSchema


class WorkoutSessionCreate(BaseSchema):
    template_id: int | None = None
    mesocycle_id: int | None = None
    name: str | None = None


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