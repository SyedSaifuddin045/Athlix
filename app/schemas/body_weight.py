from datetime import date
from pydantic import Field

from .base_schema import BaseSchema


class BodyWeightLogCreate(BaseSchema):
    weight_kg: float = Field(gt=0)
    logged_at: date
    notes: str | None = None


class BodyWeightLogUpdate(BaseSchema):
    weight_kg: float | None = Field(default=None, gt=0)
    logged_at: date | None = None
    notes: str | None = None


class BodyWeightLogResponse(BaseSchema):
    id: int
    user_id: int
    weight_kg: float
    logged_at: date
    notes: str | None
