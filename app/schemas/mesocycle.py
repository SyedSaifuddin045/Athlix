from datetime import date, datetime

from .base_schema import BaseSchema
from .workout_session import WorkoutSessionResponse

SUPPORTED_MESOCYCLE_GOALS = (
    "strength",
    "hypertrophy",
    "endurance",
    "weight_loss",
    "maintenance",
)


class MesocycleCreate(BaseSchema):
    name: str
    goal: str | None = None
    started_on: date
    ended_on: date | None = None
    weeks: int | None = None
    notes: str | None = None


class MesocycleUpdate(BaseSchema):
    name: str | None = None
    goal: str | None = None
    ended_on: date | None = None
    weeks: int | None = None
    notes: str | None = None


class MesocycleResponse(BaseSchema):
    id: int
    user_id: int
    name: str
    goal: str | None
    started_on: date
    ended_on: date | None
    weeks: int | None
    notes: str | None
    created_at: datetime


class MesocycleDetailResponse(MesocycleResponse):
    sessions: list[WorkoutSessionResponse]
