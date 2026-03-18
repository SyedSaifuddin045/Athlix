from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models.user import BodyWeightLog, User, UserProfile
from app.schemas.body_weight import (
    BodyWeightLogCreate,
    BodyWeightLogResponse,
    BodyWeightLogUpdate,
)
from app.schemas.user_profile import (
    UserProfileResponse,
    UserProfileUpdate,
)
from app.schemas.user_schema import UserResponse, UserUpdate

router = APIRouter(prefix="/users", tags=["Users"])


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _get_profile(db: Session, user_id: int) -> UserProfile | None:
    return db.execute(
        select(UserProfile).where(UserProfile.user_id == user_id)
    ).scalar_one_or_none()


def _get_body_weight_log(db: Session, user_id: int, log_id: int) -> BodyWeightLog | None:
    return db.execute(
        select(BodyWeightLog).where(
            BodyWeightLog.id == log_id,
            BodyWeightLog.user_id == user_id,
        )
    ).scalar_one_or_none()


@router.get("/me", response_model=UserResponse)
async def get_current_user_details(
    current_user: User = Depends(get_current_user),
) -> UserResponse:
    return UserResponse.model_validate(current_user)


@router.patch("/me", response_model=UserResponse)
async def update_current_user(
    payload: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> UserResponse:
    user = db.execute(
        select(User).where(User.id == current_user.id)
    ).scalar_one()

    updates = payload.model_dump(exclude_unset=True)
    if not updates:
        return UserResponse.model_validate(user)

    if "username" in updates:
        existing_username = db.execute(
            select(User).where(
                func.lower(User.username) == updates["username"].lower(),
                User.id != current_user.id,
            )
        ).scalar_one_or_none()
        if existing_username is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Username is already registered",
            )
        user.username = updates["username"]

    if "email" in updates:
        existing_email = db.execute(
            select(User).where(
                func.lower(User.email) == updates["email"],
                User.id != current_user.id,
            )
        ).scalar_one_or_none()
        if existing_email is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email is already registered",
            )
        user.email = updates["email"]

    user.updated_at = _utcnow()
    db.commit()
    db.refresh(user)

    return UserResponse.model_validate(user)


@router.get("/me/profile", response_model=UserProfileResponse)
async def get_current_user_profile(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> UserProfileResponse:
    profile = _get_profile(db, current_user.id)
    if profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User profile not found",
        )

    return UserProfileResponse.model_validate(profile)


@router.put("/me/profile", response_model=UserProfileResponse)
async def upsert_current_user_profile(
    payload: UserProfileUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> UserProfileResponse:
    profile = _get_profile(db, current_user.id)
    now = _utcnow()
    updates = payload.model_dump()

    if profile is None:
        profile = UserProfile(
            user_id=current_user.id,
            created_at=now,
            updated_at=now,
            **updates,
        )
        db.add(profile)
    else:
        for field, value in updates.items():
            setattr(profile, field, value)
        profile.updated_at = now

    db.commit()
    db.refresh(profile)

    return UserProfileResponse.model_validate(profile)


@router.get("/me/body-weight-logs", response_model=list[BodyWeightLogResponse])
async def list_body_weight_logs(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[BodyWeightLogResponse]:
    logs = db.execute(
        select(BodyWeightLog)
        .where(BodyWeightLog.user_id == current_user.id)
        .order_by(BodyWeightLog.logged_at.desc(), BodyWeightLog.id.desc())
    ).scalars().all()

    return [BodyWeightLogResponse.model_validate(log) for log in logs]


@router.post(
    "/me/body-weight-logs",
    response_model=BodyWeightLogResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_body_weight_log(
    payload: BodyWeightLogCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> BodyWeightLogResponse:
    log = BodyWeightLog(
        user_id=current_user.id,
        **payload.model_dump(),
    )
    db.add(log)
    db.commit()
    db.refresh(log)

    return BodyWeightLogResponse.model_validate(log)


@router.get("/me/body-weight-logs/{log_id}", response_model=BodyWeightLogResponse)
async def get_body_weight_log(
    log_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> BodyWeightLogResponse:
    log = _get_body_weight_log(db, current_user.id, log_id)
    if log is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Body weight log not found",
        )

    return BodyWeightLogResponse.model_validate(log)


@router.patch("/me/body-weight-logs/{log_id}", response_model=BodyWeightLogResponse)
async def update_body_weight_log(
    log_id: int,
    payload: BodyWeightLogUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> BodyWeightLogResponse:
    log = _get_body_weight_log(db, current_user.id, log_id)
    if log is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Body weight log not found",
        )

    updates = payload.model_dump(exclude_unset=True)
    for field, value in updates.items():
        setattr(log, field, value)

    db.commit()
    db.refresh(log)

    return BodyWeightLogResponse.model_validate(log)


@router.delete("/me/body-weight-logs/{log_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_body_weight_log(
    log_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Response:
    log = _get_body_weight_log(db, current_user.id, log_id)
    if log is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Body weight log not found",
        )

    db.delete(log)
    db.commit()

    return Response(status_code=status.HTTP_204_NO_CONTENT)
