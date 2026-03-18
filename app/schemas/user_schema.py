from datetime import datetime
from pydantic import StringConstraints
from typing import Annotated
from .base_schema import BaseSchema

EmailField = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        to_lower=True,
        min_length=6,
        max_length=254,
        pattern=r"^[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)+$",
    ),
]


class UserCreate(BaseSchema):
    username: str
    email: EmailField
    password: str


class UserUpdate(BaseSchema):
    username: str | None = None
    email: EmailField | None = None


class UserResponse(BaseSchema):
    id: int
    username: str
    email: EmailField
    created_at: datetime
    updated_at: datetime
