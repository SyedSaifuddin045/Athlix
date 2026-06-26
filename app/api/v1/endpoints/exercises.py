from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.exercise_cache import ExerciseCache
from app.models.exercise import ExerciseCategory
from app.models.user import User
from app.models.workout import ExerciseSet, WorkoutSession
from app.schemas.exercise_schema import (
    ExerciseDetailResponse,
    ExerciseFiltersResponse,
    ExerciseListResponse,
    ExerciseResponse,
)

router = APIRouter(prefix="/exercises", tags=["Exercises"])


def _matches(record: ExerciseResponse, field: str, value: str | None) -> bool:
    if value is None:
        return True
    actual = getattr(record, field, None)
    return actual is not None and actual.strip().lower() == value.strip().lower()


def _search(records: list[ExerciseResponse], q: str | None) -> list[ExerciseResponse]:
    if not q:
        return records
    term = q.strip().lower()
    return [r for r in records if term in r.name.lower()]


def _match_category(record: ExerciseResponse, category: str | None) -> bool:
    if category is None:
        return True
    return (record.exercise_category or "").strip().lower() == category.strip().lower()


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
    response: Response = None,
) -> ExerciseListResponse:
    if not tracked:
        all_exercises = ExerciseCache.all()
        filtered = [
            e
            for e in all_exercises
            if _matches(e, "body_part", body_part)
            and _matches(e, "equipment", equipment)
            and _matches(e, "target", target)
            and _match_category(e, category)
        ]
        filtered = _search(filtered, q)
        total = len(filtered)
        items = filtered[offset : offset + limit]

        if response is not None:
            response.headers["Cache-Control"] = "public, max-age=86400"

        return ExerciseListResponse(
            items=items,
            total=total,
            limit=limit,
            offset=offset,
        )

    tracked_ids = db.execute(
        select(ExerciseSet.exercise_id)
        .join(WorkoutSession, ExerciseSet.session_id == WorkoutSession.id)
        .where(
            WorkoutSession.user_id == current_user.id,
            WorkoutSession.is_completed.is_(True),
        )
        .distinct()
    ).scalars().all()

    if not tracked_ids:
        return ExerciseListResponse(items=[], total=0, limit=limit, offset=offset)

    all_exercises = ExerciseCache.all()
    filtered = [
        e
        for e in all_exercises
        if e.id in tracked_ids
        and _matches(e, "body_part", body_part)
        and _matches(e, "equipment", equipment)
        and _matches(e, "target", target)
        and _match_category(e, category)
    ]
    filtered = _search(filtered, q)
    total = len(filtered)
    items = filtered[offset : offset + limit]

    return ExerciseListResponse(
        items=items,
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/filters", response_model=ExerciseFiltersResponse)
async def get_exercise_filters() -> ExerciseFiltersResponse:
    all_exercises = ExerciseCache.all()
    body_parts = sorted(
        {e.body_part.strip() for e in all_exercises if e.body_part}, key=str.casefold
    )
    equipment = sorted(
        {e.equipment.strip() for e in all_exercises if e.equipment}, key=str.casefold
    )
    targets = sorted(
        {e.target.strip() for e in all_exercises if e.target}, key=str.casefold
    )
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
    response: Response = None,
) -> ExerciseDetailResponse:
    exercise = ExerciseCache.get_detail(exercise_id)
    if exercise is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Exercise not found",
        )

    if response is not None:
        response.headers["Cache-Control"] = "public, max-age=86400"

    return exercise
