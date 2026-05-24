from datetime import date, datetime, time, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.api.deps import get_current_user, get_db
from app.core.analytics import (
    MUSCLE_GROUP_ALIASES,
    SECONDARY_MUSCLE_WEIGHT,
    calculate_muscle_group_balance,
    estimate_weeks_in_range,
)
from app.models.exercise import Exercise, ExerciseSecondaryMuscle
from app.models.mesocycle import Mesocycle
from app.models.user import User
from app.models.workout import WorkoutSession
from app.schemas.analytics import (
    MuscleBalanceReportResponse,
    MuscleGroupBalanceItemResponse,
    MuscleGroupExerciseItemResponse,
)

router = APIRouter(prefix="/analytics", tags=["Analytics"])


def _utc_start_of_day(value: date) -> datetime:
    return datetime.combine(value, time.min, tzinfo=timezone.utc)


@router.get("/muscle-balance", response_model=MuscleBalanceReportResponse)
async def get_muscle_balance_report(
    weeks: int = Query(default=4, ge=1, le=52),
    reference_date: date | None = Query(default=None),
    mesocycle_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> MuscleBalanceReportResponse:
    weeks_in_scope = weeks
    statement = (
        select(WorkoutSession)
        .options(selectinload(WorkoutSession.sets))
        .where(
            WorkoutSession.user_id == current_user.id,
            WorkoutSession.is_completed.is_(True),
        )
        .order_by(WorkoutSession.started_at.asc(), WorkoutSession.id.asc())
    )

    if mesocycle_id is not None:
        mesocycle = db.execute(
            select(Mesocycle).where(
                Mesocycle.id == mesocycle_id,
                Mesocycle.user_id == current_user.id,
            )
        ).scalar_one_or_none()
        if mesocycle is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Mesocycle not found",
            )
        statement = statement.where(WorkoutSession.mesocycle_id == mesocycle.id)
        weeks_in_scope = (
            mesocycle.weeks
            if mesocycle.weeks is not None and mesocycle.weeks > 0
            else estimate_weeks_in_range(mesocycle.started_on, mesocycle.ended_on)
        )
    else:
        effective_reference_date = reference_date or datetime.now(timezone.utc).date()
        window_start = effective_reference_date - timedelta(days=weeks * 7 - 1)
        statement = statement.where(WorkoutSession.started_at >= _utc_start_of_day(window_start))

    sessions = db.execute(statement).scalars().all()
    exercise_ids = {
        exercise_set.exercise_id
        for session in sessions
        for exercise_set in session.sets
    }
    exercises_by_id: dict[str, Exercise] = {}
    secondary_by_exercise: dict[str, list[str]] = {}
    if exercise_ids:
        exercises_by_id = {
            exercise.id: exercise
            for exercise in db.execute(
                select(Exercise).where(Exercise.id.in_(exercise_ids))
            ).scalars().all()
        }
        secondary_records = db.execute(
            select(ExerciseSecondaryMuscle).where(
                ExerciseSecondaryMuscle.exercise_id.in_(exercise_ids)
            )
        ).scalars().all()
        for rec in secondary_records:
            secondary_by_exercise.setdefault(rec.exercise_id, []).append(rec.muscle)

    muscle_groups: list[tuple[str, str, float]] = []
    for session in sessions:
        for exercise_set in session.sets:
            if exercise_set.set_type.lower() == "warmup":
                continue
            exercise = exercises_by_id.get(exercise_set.exercise_id)
            if exercise is None:
                continue
            raw_target = (exercise.target or exercise.body_part or "").strip().lower()
            primary = MUSCLE_GROUP_ALIASES.get(raw_target)
            if primary:
                muscle_groups.append((primary, exercise.name, 1.0))
            for secondary_raw in secondary_by_exercise.get(exercise_set.exercise_id, []):
                canonical_sec = MUSCLE_GROUP_ALIASES.get(secondary_raw.strip().lower())
                if canonical_sec and canonical_sec != primary:
                    muscle_groups.append((canonical_sec, exercise.name, SECONDARY_MUSCLE_WEIGHT))

    report = calculate_muscle_group_balance(
        muscle_groups,
        weeks_in_scope=weeks_in_scope,
    )

    return MuscleBalanceReportResponse(
        weeks_in_scope=weeks_in_scope,
        items=[
            MuscleGroupBalanceItemResponse(
                muscle_group=item.muscle_group,
                weekly_sets=item.weekly_sets,
                average_weekly_sets=item.average_weekly_sets,
                score=item.score,
                status=item.status,
                recommendation=item.recommendation,
                exercises=[
                    MuscleGroupExerciseItemResponse(
                        exercise_name=ex.exercise_name,
                        completed_sets=ex.completed_sets,
                        average_weekly_sets=ex.average_weekly_sets,
                    )
                    for ex in (item.exercises or [])
                ],
            )
            for item in report
        ],
    )
