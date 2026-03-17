from datetime import datetime, date
from .base_schema import BaseSchema


class PersonalRecordCreate(BaseSchema):
    exercise_id: str
    record_type: str
    value: float
    achieved_on: date
    session_id: int | None = None
    set_id: int | None = None
    notes: str | None = None


class PersonalRecordResponse(BaseSchema):
    id: int
    user_id: int
    exercise_id: str
    record_type: str
    value: float
    achieved_on: date
    session_id: int | None
    set_id: int | None
    notes: str | None
    created_at: datetime