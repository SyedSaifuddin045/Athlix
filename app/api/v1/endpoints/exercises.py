from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.api.deps import get_current_user, get_db
from app.models.exercise import Exercise, ExerciseCategory
from app.models.user import User
from app.models.workout import ExerciseSet, WorkoutSession
from app.schemas.exercise_schema import (
    ExerciseDetailResponse,
    ExerciseFiltersResponse,
    ExerciseListResponse,
    ExerciseResponse,
)

router = APIRouter(prefix="/exercises", tags=["Exercises"])


def _apply_filters(
    statement,
    *,
    q: str | None,
    body_part: str | None,
    equipment: str | None,
    target: str | None,
    category: str | None,
):
    if q:
        search_term = f"%{q.strip().lower()}%"
        statement = statement.where(func.lower(Exercise.name).like(search_term))

    if body_part:
        statement = statement.where(func.lower(Exercise.body_part) == body_part.strip().lower())

    if equipment:
        statement = statement.where(func.lower(Exercise.equipment) == equipment.strip().lower())

    if target:
        statement = statement.where(func.lower(Exercise.target) == target.strip().lower())

    if category:
        statement = statement.where(Exercise.exercise_category == category.strip().lower())

    return statement


@router.get("", response_model=ExerciseListResponse)
async def list_exercises(
    q: str | None = Query(default=None, min_length=1, max_length=100),
    body_part: str | None = Query(default=None, min_length=1, max_length=100),
    equipment: str | None = Query(default=None, min_length=1, max_length=100),
    target: str | None = Query(default=None, min_length=1, max_length=100),
    category: str | None = Query(default=None, min_length=1, max_length=20),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    tracked: bool = Query(default=False),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ExerciseListResponse:
    base_statement = _apply_filters(
        select(Exercise),
        q=q,
        body_part=body_part,
        equipment=equipment,
        target=target,
        category=category,
    )

    if tracked:
        tracked_ids = db.execute(
            select(ExerciseSet.exercise_id)
            .join(WorkoutSession, ExerciseSet.session_id == WorkoutSession.id)
            .where(
                WorkoutSession.user_id == current_user.id,
                WorkoutSession.is_completed.is_(True),
            )
            .distinct()
        ).scalars().all()
        if tracked_ids:
            base_statement = base_statement.where(Exercise.id.in_(tracked_ids))
        else:
            base_statement = base_statement.where(False)

    total = db.execute(
        select(func.count()).select_from(base_statement.order_by(None).subquery())
    ).scalar_one()

    exercises = db.execute(
        base_statement
        .order_by(Exercise.name.asc(), Exercise.id.asc())
        .offset(offset)
        .limit(limit)
    ).scalars().all()

    return ExerciseListResponse(
        items=[ExerciseResponse.model_validate(exercise) for exercise in exercises],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/filters", response_model=ExerciseFiltersResponse)
async def get_exercise_filters(
    db: Session = Depends(get_db),
) -> ExerciseFiltersResponse:
    body_parts = db.execute(
        select(Exercise.body_part)
        .where(Exercise.body_part.is_not(None))
        .distinct()
        .order_by(Exercise.body_part.asc())
    ).scalars().all()
    equipment = db.execute(
        select(Exercise.equipment)
        .where(Exercise.equipment.is_not(None))
        .distinct()
        .order_by(Exercise.equipment.asc())
    ).scalars().all()
    targets = db.execute(
        select(Exercise.target)
        .where(Exercise.target.is_not(None))
        .distinct()
        .order_by(Exercise.target.asc())
    ).scalars().all()

    categories = [c.value for c in ExerciseCategory]

    return ExerciseFiltersResponse(
        body_parts=body_parts,
        equipment=equipment,
        targets=targets,
        categories=categories,
    )


@router.get("/{exercise_id}", response_model=ExerciseDetailResponse)
async def get_exercise(
    exercise_id: str,
    db: Session = Depends(get_db),
) -> ExerciseDetailResponse:
    exercise = db.execute(
        select(Exercise)
        .options(
            selectinload(Exercise.instructions),
            selectinload(Exercise.secondary_muscles),
        )
        .where(Exercise.id == exercise_id)
    ).scalar_one_or_none()
    if exercise is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Exercise not found",
        )

    return ExerciseDetailResponse.model_validate(exercise)
