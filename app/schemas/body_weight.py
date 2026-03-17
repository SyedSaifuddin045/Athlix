from datetime import date
from .base_schema import BaseSchema


class BodyWeightLogCreate(BaseSchema):
    weight_kg: float
    logged_at: date
    notes: str | None = None


class BodyWeightLogResponse(BaseSchema):
    id: int
    user_id: int
    weight_kg: float
    logged_at: date
    notes: str | None