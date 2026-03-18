from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.core.analytics import (
    DEFAULT_E1RM_FORMULA,
    SUPPORTED_E1RM_FORMULAS,
    build_session_exercise_summaries,
    calculate_weekly_volume_summaries,
    calculate_workout_streaks,
    detect_progressive_overload,
)
from app.models.exercise import Exercise
from app.models.user import User
from app.models.workout import ExerciseSet, WorkoutSession
from app.schemas.progress import (
    E1RMFormulaResponse,
    ExerciseProgressPointResponse,
    ExerciseProgressResponse,
    ProgressiveOverloadResponse,
    WeeklyVolumeProgressPointResponse,
    WorkoutStreaksResponse,
)

router = APIRouter(prefix="/progress", tags=["Progress"])


@router.get("/{exercise_id}", response_model=ExerciseProgressResponse)
async def get_exercise_progress(
    exercise_id: str,
    formula: str = Query(default=DEFAULT_E1RM_FORMULA),
    reference_date: date | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ExerciseProgressResponse:
    normalized_formula = formula.lower()
    if normalized_formula not in SUPPORTED_E1RM_FORMULAS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Unsupported e1RM formula",
        )

    exercise = db.execute(
        select(Exercise).where(Exercise.id == exercise_id)
    ).scalar_one_or_none()
    if exercise is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Exercise not found",
        )

    rows = db.execute(
        select(ExerciseSet, WorkoutSession)
        .join(WorkoutSession, ExerciseSet.session_id == WorkoutSession.id)
        .where(
            WorkoutSession.user_id == current_user.id,
            WorkoutSession.is_completed.is_(True),
            ExerciseSet.exercise_id == exercise_id,
        )
        .order_by(WorkoutSession.started_at.asc(), ExerciseSet.set_number.asc(), ExerciseSet.id.asc())
    ).all()

    session_summaries = build_session_exercise_summaries(
        rows,
        default_formula=normalized_formula,
    )
    weekly_volume = calculate_weekly_volume_summaries(session_summaries)
    overload_points = detect_progressive_overload(session_summaries)

    completed_session_datetimes = db.execute(
        select(WorkoutSession.started_at)
        .where(
            WorkoutSession.user_id == current_user.id,
            WorkoutSession.is_completed.is_(True),
        )
        .order_by(WorkoutSession.started_at.asc())
    ).scalars().all()
    workout_streaks = calculate_workout_streaks(
        list(completed_session_datetimes),
        reference_date=reference_date,
    )

    progress_points = [
        ExerciseProgressPointResponse(
            session_id=summary.session_id,
            performed_at=summary.performed_at,
            best_set_id=summary.best_set_id,
            weight_kg=summary.best_weight_kg,
            reps=summary.best_reps,
            default_e1rm=summary.default_e1rm,
            formulas=E1RMFormulaResponse(**summary.e1rm_formulas),
            volume_load=summary.volume_load,
        )
        for summary in session_summaries
    ]

    return ExerciseProgressResponse(
        exercise_id=exercise.id,
        exercise_name=exercise.name,
        default_formula=normalized_formula,
        e1rm_history=progress_points,
        volume_history=progress_points,
        weekly_volume_history=[
            WeeklyVolumeProgressPointResponse(
                week_start=item.week_start,
                week_end=item.week_end,
                volume_load=item.volume_load,
            )
            for item in weekly_volume
        ],
        progressive_overload=[
            ProgressiveOverloadResponse(
                current_session_id=item.current_session_id,
                previous_session_id=item.previous_session_id,
                performed_at=item.performed_at,
                current_volume_load=item.current_volume_load,
                previous_volume_load=item.previous_volume_load,
                volume_load_delta=item.volume_load_delta,
                current_best_weight_kg=item.current_best_weight_kg,
                previous_best_weight_kg=item.previous_best_weight_kg,
                best_weight_delta=item.best_weight_delta,
                current_default_e1rm=item.current_default_e1rm,
                previous_default_e1rm=item.previous_default_e1rm,
                default_e1rm_delta=item.default_e1rm_delta,
                improved_metrics=item.improved_metrics,
            )
            for item in overload_points
        ],
        workout_streaks=WorkoutStreaksResponse(
            current_daily_streak=workout_streaks.current_daily_streak,
            longest_daily_streak=workout_streaks.longest_daily_streak,
            current_weekly_streak=workout_streaks.current_weekly_streak,
            longest_weekly_streak=workout_streaks.longest_weekly_streak,
        ),
    )
