from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.core.config import settings
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_refresh_token,
    hash_password,
    verify_password,
)
from app.models.user import User
from app.schemas.auth import AuthResponse, LoginRequest, RefreshTokenRequest, RegisterRequest
from app.schemas.user_schema import UserResponse

router = APIRouter(prefix="/auth", tags=["Auth"])


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _build_auth_response(user: User) -> AuthResponse:
    return AuthResponse(
        access_token=create_access_token(subject=str(user.id)),
        refresh_token=create_refresh_token(subject=str(user.id)),
        expires_in=settings.access_token_expire_minutes * 60,
        refresh_expires_in=int(timedelta(days=settings.refresh_token_expire_days).total_seconds()),
        user=UserResponse.model_validate(user),
    )


@router.post(
    "/register",
    response_model=AuthResponse,
    status_code=status.HTTP_201_CREATED,
)
async def register_user(payload: RegisterRequest, db: Session = Depends(get_db)) -> AuthResponse:
    existing_username = db.execute(
        select(User).where(func.lower(User.username) == payload.username.lower())
    ).scalar_one_or_none()
    if existing_username is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username is already registered",
        )

    existing_email = db.execute(
        select(User).where(func.lower(User.email) == payload.email)
    ).scalar_one_or_none()
    if existing_email is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email is already registered",
        )

    now = _utcnow()
    user = User(
        username=payload.username,
        email=payload.email,
        password_hash=hash_password(payload.password),
        created_at=now,
        updated_at=now,
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    return _build_auth_response(user)


@router.post("/login", response_model=AuthResponse)
async def login_user(payload: LoginRequest, db: Session = Depends(get_db)) -> AuthResponse:
    invalid_credentials = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid email or password",
        headers={"WWW-Authenticate": "Bearer"},
    )

    user = db.execute(
        select(User).where(func.lower(User.email) == payload.email)
    ).scalar_one_or_none()
    if user is None or not verify_password(payload.password, user.password_hash):
        raise invalid_credentials

    return _build_auth_response(user)


@router.post("/refresh", response_model=AuthResponse)
async def refresh_tokens(
    payload: RefreshTokenRequest,
    db: Session = Depends(get_db),
) -> AuthResponse:
    invalid_refresh_token = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid refresh token",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        token_payload = decode_refresh_token(payload.refresh_token)
        subject = token_payload.get("sub")
    except ValueError as exc:
        raise invalid_refresh_token from exc

    if not subject:
        raise invalid_refresh_token

    try:
        user_id = int(subject)
    except (TypeError, ValueError) as exc:
        raise invalid_refresh_token from exc

    user = db.execute(
        select(User).where(User.id == user_id)
    ).scalar_one_or_none()
    if user is None:
        raise invalid_refresh_token

    return _build_auth_response(user)


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)) -> UserResponse:
    return UserResponse.model_validate(current_user)
