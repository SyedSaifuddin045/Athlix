from pydantic import Field, StringConstraints
from typing import Annotated

from .base_schema import BaseSchema
from .user_schema import EmailField, UserResponse, UsernameField

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


class RefreshTokenRequest(BaseSchema):
    refresh_token: str


class AuthResponse(BaseSchema):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = Field(..., description="Access token lifetime in seconds")
    refresh_expires_in: int = Field(..., description="Refresh token lifetime in seconds")
    user: UserResponse
