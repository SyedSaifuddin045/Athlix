from datetime import datetime
from pydantic import EmailStr
from .base_schema import BaseSchema


class UserCreate(BaseSchema):
    username: str
    email: EmailStr
    password: str


class UserUpdate(BaseSchema):
    username: str | None = None
    email: EmailStr | None = None


class UserResponse(BaseSchema):
    id: int
    username: str
    email: EmailStr
    created_at: datetime
    updated_at: datetime