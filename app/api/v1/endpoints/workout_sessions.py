from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.api.deps import get_current_user, get_db
from app.models.exercise import Exercise
from app.models.mesocycle import Mesocycle
from app.models.user import User
from app.models.workout import ExerciseSet, WorkoutSession, WorkoutTemplate
from app.schemas.exercise_set import (
    ExerciseSetCreate,
    ExerciseSetResponse,
    ExerciseSetUpdate,
)
from app.schemas.workout_session import (
    WorkoutSessionCreate,
    WorkoutSessionDetailResponse,
    WorkoutSessionResponse,
    WorkoutSessionUpdate,
)

router = APIRouter(prefix="/workout-sessions", tags=["Workout Sessions"])


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _get_workout_session(
    db: Session,
    user_id: int,
    session_id: int,
    *,
    with_sets: bool = False,
) -> WorkoutSession | None:
    statement = select(WorkoutSession).where(
        WorkoutSession.id == session_id,
        WorkoutSession.user_id == user_id,
    )
    if with_sets:
        statement = statement.options(selectinload(WorkoutSession.sets))

    return db.execute(statement).scalar_one_or_none()


def _get_exercise_set(
    db: Session,
    session_id: int,
    set_id: int,
) -> ExerciseSet | None:
    return db.execute(
        select(ExerciseSet).where(
            ExerciseSet.id == set_id,
            ExerciseSet.session_id == session_id,
        )
    ).scalar_one_or_none()


def _ensure_exercise_exists(db: Session, exercise_id: str) -> None:
    exercise = db.execute(
        select(Exercise.id).where(Exercise.id == exercise_id)
    ).scalar_one_or_none()
    if exercise is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Exercise not found",
        )


def _validate_template_reference(
    db: Session,
    user_id: int,
    template_id: int | None,
) -> None:
    if template_id is None:
        return

    template = db.execute(
        select(WorkoutTemplate.id).where(
            WorkoutTemplate.id == template_id,
            WorkoutTemplate.user_id == user_id,
        )
    ).scalar_one_or_none()
    if template is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workout template not found",
        )


def _validate_mesocycle_reference(
    db: Session,
    user_id: int,
    mesocycle_id: int | None,
) -> None:
    if mesocycle_id is None:
        return

    mesocycle = db.execute(
        select(Mesocycle.id).where(
            Mesocycle.id == mesocycle_id,
            Mesocycle.user_id == user_id,
        )
    ).scalar_one_or_none()
    if mesocycle is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Mesocycle not found",
        )


@router.get("", response_model=list[WorkoutSessionResponse])
async def list_workout_sessions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[WorkoutSessionResponse]:
    sessions = db.execute(
        select(WorkoutSession)
        .where(WorkoutSession.user_id == current_user.id)
        .order_by(WorkoutSession.started_at.desc(), WorkoutSession.id.desc())
    ).scalars().all()

    return [WorkoutSessionResponse.model_validate(session) for session in sessions]


@router.post(
    "",
    response_model=WorkoutSessionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_workout_session(
    payload: WorkoutSessionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> WorkoutSessionResponse:
    payload_data = payload.model_dump()
    _validate_template_reference(db, current_user.id, payload_data["template_id"])
    _validate_mesocycle_reference(db, current_user.id, payload_data["mesocycle_id"])

    started_at = payload_data.pop("started_at") or _utcnow()
    is_completed = payload_data.pop("is_completed")
    finished_at = payload_data.get("finished_at")

    session = WorkoutSession(
        user_id=current_user.id,
        started_at=started_at,
        is_completed=is_completed or finished_at is not None,
        **payload_data,
    )
    db.add(session)
    db.commit()
    db.refresh(session)

    return WorkoutSessionResponse.model_validate(session)


@router.get("/{session_id}", response_model=WorkoutSessionDetailResponse)
async def get_workout_session(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> WorkoutSessionDetailResponse:
    session = _get_workout_session(
        db,
        current_user.id,
        session_id,
        with_sets=True,
    )
    if session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workout session not found",
        )

    return WorkoutSessionDetailResponse.model_validate(session)


@router.patch("/{session_id}", response_model=WorkoutSessionResponse)
async def update_workout_session(
    session_id: int,
    payload: WorkoutSessionUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> WorkoutSessionResponse:
    session = _get_workout_session(db, current_user.id, session_id)
    if session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workout session not found",
        )

    updates = payload.model_dump(exclude_unset=True)
    if "template_id" in updates:
        _validate_template_reference(db, current_user.id, updates["template_id"])
    if "mesocycle_id" in updates:
        _validate_mesocycle_reference(db, current_user.id, updates["mesocycle_id"])
    if "finished_at" in updates and "is_completed" not in updates and updates["finished_at"] is not None:
        updates["is_completed"] = True

    if not updates:
        return WorkoutSessionResponse.model_validate(session)

    for field, value in updates.items():
        setattr(session, field, value)

    db.commit()
    db.refresh(session)

    return WorkoutSessionResponse.model_validate(session)


@router.delete("/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_workout_session(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Response:
    session = _get_workout_session(db, current_user.id, session_id)
    if session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workout session not found",
        )

    db.delete(session)
    db.commit()

    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{session_id}/sets", response_model=list[ExerciseSetResponse])
async def list_exercise_sets(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[ExerciseSetResponse]:
    session = _get_workout_session(db, current_user.id, session_id)
    if session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workout session not found",
        )

    exercise_sets = db.execute(
        select(ExerciseSet)
        .where(ExerciseSet.session_id == session_id)
        .order_by(ExerciseSet.set_number.asc(), ExerciseSet.id.asc())
    ).scalars().all()

    return [ExerciseSetResponse.model_validate(item) for item in exercise_sets]


@router.post(
    "/{session_id}/sets",
    response_model=ExerciseSetResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_exercise_set(
    session_id: int,
    payload: ExerciseSetCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ExerciseSetResponse:
    session = _get_workout_session(db, current_user.id, session_id)
    if session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workout session not found",
        )

    _ensure_exercise_exists(db, payload.exercise_id)
    payload_data = payload.model_dump()
    logged_at = payload_data.pop("logged_at") or _utcnow()

    exercise_set = ExerciseSet(
        session_id=session_id,
        logged_at=logged_at,
        **payload_data,
    )
    db.add(exercise_set)
    db.commit()
    db.refresh(exercise_set)

    return ExerciseSetResponse.model_validate(exercise_set)


@router.get("/{session_id}/sets/{set_id}", response_model=ExerciseSetResponse)
async def get_exercise_set(
    session_id: int,
    set_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ExerciseSetResponse:
    session = _get_workout_session(db, current_user.id, session_id)
    if session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workout session not found",
        )

    exercise_set = _get_exercise_set(db, session_id, set_id)
    if exercise_set is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Exercise set not found",
        )

    return ExerciseSetResponse.model_validate(exercise_set)


@router.patch("/{session_id}/sets/{set_id}", response_model=ExerciseSetResponse)
async def update_exercise_set(
    session_id: int,
    set_id: int,
    payload: ExerciseSetUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ExerciseSetResponse:
    session = _get_workout_session(db, current_user.id, session_id)
    if session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workout session not found",
        )

    exercise_set = _get_exercise_set(db, session_id, set_id)
    if exercise_set is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Exercise set not found",
        )

    updates = payload.model_dump(exclude_unset=True)
    if "exercise_id" in updates and updates["exercise_id"] is not None:
        _ensure_exercise_exists(db, updates["exercise_id"])

    if not updates:
        return ExerciseSetResponse.model_validate(exercise_set)

    for field, value in updates.items():
        setattr(exercise_set, field, value)

    db.commit()
    db.refresh(exercise_set)

    return ExerciseSetResponse.model_validate(exercise_set)


@router.delete("/{session_id}/sets/{set_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_exercise_set(
    session_id: int,
    set_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Response:
    session = _get_workout_session(db, current_user.id, session_id)
    if session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workout session not found",
        )

    exercise_set = _get_exercise_set(db, session_id, set_id)
    if exercise_set is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Exercise set not found",
        )

    db.delete(exercise_set)
    db.commit()

    return Response(status_code=status.HTTP_204_NO_CONTENT)
