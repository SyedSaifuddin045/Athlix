from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.core.analytics import calculate_workout_streaks
from app.models.mesocycle import Mesocycle
from app.models.records import PersonalRecord
from app.models.user import BodyWeightLog, User, UserProfile
from app.models.workout import WorkoutSession, WorkoutTemplate
from app.schemas.body_weight import (
    BodyWeightLogCreate,
    BodyWeightLogResponse,
    BodyWeightLogUpdate,
)
from app.schemas.mesocycle import MesocycleResponse
from app.schemas.personal_record import PersonalRecordResponse
from app.schemas.progress import WorkoutStreaksResponse
from app.schemas.user_profile import (
    UserProfileResponse,
    UserProfileUpdate,
)
from app.schemas.user_schema import UserResponse, UserUpdate
from app.schemas.user_overview import (
    UserOverviewResponse,
    UserOverviewStatsResponse,
)
from app.schemas.workout_session import WorkoutSessionResponse

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


@router.get("/me/overview", response_model=UserOverviewResponse)
async def get_current_user_overview(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> UserOverviewResponse:
    profile = _get_profile(db, current_user.id)
    latest_body_weight_log = db.execute(
        select(BodyWeightLog)
        .where(BodyWeightLog.user_id == current_user.id)
        .order_by(BodyWeightLog.logged_at.desc(), BodyWeightLog.id.desc())
    ).scalars().first()

    today = _utcnow().date()
    active_mesocycle = db.execute(
        select(Mesocycle)
        .where(
            Mesocycle.user_id == current_user.id,
            Mesocycle.started_on <= today,
            or_(
                Mesocycle.ended_on.is_(None),
                Mesocycle.ended_on >= today,
            ),
        )
        .order_by(Mesocycle.started_on.desc(), Mesocycle.id.desc())
    ).scalars().first()

    latest_completed_session = db.execute(
        select(WorkoutSession)
        .where(
            WorkoutSession.user_id == current_user.id,
            WorkoutSession.is_completed.is_(True),
        )
        .order_by(WorkoutSession.started_at.desc(), WorkoutSession.id.desc())
    ).scalars().first()

    recent_personal_records = db.execute(
        select(PersonalRecord)
        .where(PersonalRecord.user_id == current_user.id)
        .order_by(
            PersonalRecord.achieved_on.desc(),
            PersonalRecord.created_at.desc(),
            PersonalRecord.id.desc(),
        )
        .limit(5)
    ).scalars().all()

    completed_session_datetimes = db.execute(
        select(WorkoutSession.started_at)
        .where(
            WorkoutSession.user_id == current_user.id,
            WorkoutSession.is_completed.is_(True),
        )
        .order_by(WorkoutSession.started_at.asc())
    ).scalars().all()
    streaks = calculate_workout_streaks(list(completed_session_datetimes))

    total_workout_templates = db.execute(
        select(func.count())
        .select_from(WorkoutTemplate)
        .where(WorkoutTemplate.user_id == current_user.id)
    ).scalar_one()
    total_sessions = db.execute(
        select(func.count())
        .select_from(WorkoutSession)
        .where(WorkoutSession.user_id == current_user.id)
    ).scalar_one()
    completed_sessions = db.execute(
        select(func.count())
        .select_from(WorkoutSession)
        .where(
            WorkoutSession.user_id == current_user.id,
            WorkoutSession.is_completed.is_(True),
        )
    ).scalar_one()
    personal_record_count = db.execute(
        select(func.count())
        .select_from(PersonalRecord)
        .where(PersonalRecord.user_id == current_user.id)
    ).scalar_one()

    return UserOverviewResponse(
        user=UserResponse.model_validate(current_user),
        has_profile=profile is not None,
        profile=UserProfileResponse.model_validate(profile) if profile is not None else None,
        latest_body_weight_log=(
            BodyWeightLogResponse.model_validate(latest_body_weight_log)
            if latest_body_weight_log is not None
            else None
        ),
        active_mesocycle=(
            MesocycleResponse.model_validate(active_mesocycle)
            if active_mesocycle is not None
            else None
        ),
        latest_completed_session=(
            WorkoutSessionResponse.model_validate(latest_completed_session)
            if latest_completed_session is not None
            else None
        ),
        recent_personal_records=[
            PersonalRecordResponse.model_validate(record)
            for record in recent_personal_records
        ],
        workout_streaks=WorkoutStreaksResponse(
            current_daily_streak=streaks.current_daily_streak,
            longest_daily_streak=streaks.longest_daily_streak,
            current_weekly_streak=streaks.current_weekly_streak,
            longest_weekly_streak=streaks.longest_weekly_streak,
        ),
        stats=UserOverviewStatsResponse(
            total_workout_templates=total_workout_templates,
            total_sessions=total_sessions,
            completed_sessions=completed_sessions,
            personal_record_count=personal_record_count,
        ),
    )


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
