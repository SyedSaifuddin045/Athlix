from pydantic import Field, StringConstraints
from typing import Annotated

from .base_schema import BaseSchema
from .user_schema import UserResponse

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

UsernameField = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        min_length=3,
        max_length=50,
        pattern=r"^[A-Za-z0-9_.-]+$",
    ),
]

PasswordField = Annotated[
    str,
    StringConstraints(
        min_length=8,
        max_length=128,
    ),
]


class RegisterRequest(BaseSchema):
    username: UsernameField
    email: EmailField
    password: PasswordField


class LoginRequest(BaseSchema):
    email: EmailField
    password: PasswordField


class AuthResponse(BaseSchema):
    access_token: str
    token_type: str = "bearer"
    expires_in: int = Field(..., description="Access token lifetime in seconds")
    user: UserResponse
