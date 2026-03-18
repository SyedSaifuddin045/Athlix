from datetime import date, datetime
from pydantic import Field

from .base_schema import BaseSchema


class UserProfileCreate(BaseSchema):
    display_name: str | None = None
    date_of_birth: date | None = None
    gender: str | None = None
    height_cm: float | None = Field(default=None, gt=0)
    weight_kg: float | None = Field(default=None, gt=0)
    fitness_level: str | None = None
    preferred_unit: str | None = None


class UserProfileUpdate(BaseSchema):
    display_name: str | None = None
    date_of_birth: date | None = None
    gender: str | None = None
    height_cm: float | None = Field(default=None, gt=0)
    weight_kg: float | None = Field(default=None, gt=0)
    fitness_level: str | None = None
    preferred_unit: str | None = None


class UserProfileResponse(BaseSchema):
    id: int
    user_id: int
    display_name: str | None
    date_of_birth: date | None
    gender: str | None
    height_cm: float | None
    weight_kg: float | None
    fitness_level: str | None
    preferred_unit: str | None
    created_at: datetime
    updated_at: datetime
