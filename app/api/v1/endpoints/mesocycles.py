from datetime import date, datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session, selectinload

from app.api.deps import get_current_user, get_db
from app.core.analytics import (
    DEFAULT_E1RM_FORMULA,
    SUPPORTED_E1RM_FORMULAS,
    build_exercise_block_summaries,
    build_session_effort_summaries,
    calculate_muscle_group_balance,
    compare_training_blocks,
    detect_deload_suggestion,
    estimate_weeks_in_range,
    summarize_training_block,
)
from app.models.exercise import Exercise
from app.models.mesocycle import Mesocycle
from app.models.user import User
from app.models.workout import WorkoutSession
from app.schemas.analytics import (
    DeloadSuggestionResponse,
    ExerciseBlockComparisonResponse,
    MesocycleAnalyticsResponse,
    MuscleBalanceReportResponse,
    MuscleGroupBalanceItemResponse,
    TrainingBlockDeltaResponse,
    TrainingBlockSummaryResponse,
    WeeklyEffortResponse,
)
from app.schemas.mesocycle import (
    MesocycleCreate,
    MesocycleDetailResponse,
    MesocycleResponse,
    MesocycleUpdate,
)

router = APIRouter(prefix="/mesocycles", tags=["Mesocycles"])

ALLOWED_GOALS = {
    "strength",
    "hypertrophy",
    "endurance",
    "weight_loss",
    "maintenance",
}


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _resolve_muscle_group(exercise: Exercise | None) -> str | None:
    if exercise is None:
        return None
    raw_group = (exercise.target or exercise.body_part or "").strip().lower()
    return raw_group or None


def _calculate_delta(current: float | None, previous: float | None) -> float | None:
    if current is not None and previous is not None:
        return round(current - previous, 2)
    if current is not None:
        return round(current, 2)
    return None


def _load_completed_sessions_for_mesocycle(
    db: Session,
    user_id: int,
    mesocycle_id: int,
) -> list[WorkoutSession]:
    return db.execute(
        select(WorkoutSession)
        .options(selectinload(WorkoutSession.sets))
        .where(
            WorkoutSession.user_id == user_id,
            WorkoutSession.mesocycle_id == mesocycle_id,
            WorkoutSession.is_completed.is_(True),
        )
        .order_by(WorkoutSession.started_at.asc(), WorkoutSession.id.asc())
    ).scalars().all()


def _resolve_mesocycle_weeks(
    mesocycle: Mesocycle,
    sessions: list[WorkoutSession],
) -> int:
    if mesocycle.weeks is not None and mesocycle.weeks > 0:
        return mesocycle.weeks

    inferred_end: date | None = mesocycle.ended_on
    if inferred_end is None and sessions:
        inferred_end = max(session.started_at.date() for session in sessions)

    return estimate_weeks_in_range(mesocycle.started_on, inferred_end)


def _serialize_training_block_summary(summary) -> TrainingBlockSummaryResponse:
    return TrainingBlockSummaryResponse(
        completed_sessions=summary.completed_sessions,
        total_sets=summary.total_sets,
        distinct_exercises=summary.distinct_exercises,
        total_volume_load=summary.total_volume_load,
        average_session_volume_load=summary.average_session_volume_load,
        average_session_rpe=summary.average_session_rpe,
    )


def _get_mesocycle(
    db: Session,
    user_id: int,
    mesocycle_id: int,
    *,
    with_sessions: bool = False,
) -> Mesocycle | None:
    statement = select(Mesocycle).where(
        Mesocycle.id == mesocycle_id,
        Mesocycle.user_id == user_id,
    )
    if with_sessions:
        statement = statement.options(selectinload(Mesocycle.sessions))

    return db.execute(statement).scalar_one_or_none()


def _validate_mesocycle_payload(
    *,
    goal: str | None,
    started_on,
    ended_on,
    weeks,
) -> None:
    if goal is not None and goal not in ALLOWED_GOALS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Unsupported mesocycle goal",
        )

    if weeks is not None and weeks <= 0:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Weeks must be greater than zero",
        )

    if started_on is not None and ended_on is not None and ended_on < started_on:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Mesocycle end date cannot be before the start date",
        )


@router.get("", response_model=list[MesocycleResponse])
async def list_mesocycles(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[MesocycleResponse]:
    mesocycles = db.execute(
        select(Mesocycle)
        .where(Mesocycle.user_id == current_user.id)
        .order_by(Mesocycle.started_on.desc(), Mesocycle.id.desc())
    ).scalars().all()

    return [MesocycleResponse.model_validate(mesocycle) for mesocycle in mesocycles]


@router.post(
    "",
    response_model=MesocycleResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_mesocycle(
    payload: MesocycleCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> MesocycleResponse:
    payload_data = payload.model_dump()
    _validate_mesocycle_payload(
        goal=payload_data["goal"],
        started_on=payload_data["started_on"],
        ended_on=payload_data["ended_on"],
        weeks=payload_data["weeks"],
    )

    mesocycle = Mesocycle(
        user_id=current_user.id,
        created_at=_utcnow(),
        **payload_data,
    )
    db.add(mesocycle)
    db.commit()
    db.refresh(mesocycle)

    return MesocycleResponse.model_validate(mesocycle)


@router.get("/{mesocycle_id}/analytics", response_model=MesocycleAnalyticsResponse)
async def get_mesocycle_analytics(
    mesocycle_id: int,
    formula: str = Query(default=DEFAULT_E1RM_FORMULA),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> MesocycleAnalyticsResponse:
    normalized_formula = formula.lower()
    if normalized_formula not in SUPPORTED_E1RM_FORMULAS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Unsupported e1RM formula",
        )

    mesocycle = _get_mesocycle(db, current_user.id, mesocycle_id)
    if mesocycle is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Mesocycle not found",
        )

    previous_mesocycle = db.execute(
        select(Mesocycle)
        .where(
            Mesocycle.user_id == current_user.id,
            or_(
                Mesocycle.started_on < mesocycle.started_on,
                and_(
                    Mesocycle.started_on == mesocycle.started_on,
                    Mesocycle.id < mesocycle.id,
                ),
            ),
        )
        .order_by(Mesocycle.started_on.desc(), Mesocycle.id.desc())
    ).scalars().first()

    current_sessions = _load_completed_sessions_for_mesocycle(
        db,
        current_user.id,
        mesocycle.id,
    )
    previous_sessions = []
    if previous_mesocycle is not None:
        previous_sessions = _load_completed_sessions_for_mesocycle(
            db,
            current_user.id,
            previous_mesocycle.id,
        )

    exercise_ids = {
        exercise_set.exercise_id
        for session in [*current_sessions, *previous_sessions]
        for exercise_set in session.sets
    }
    exercises_by_id: dict[str, Exercise] = {}
    if exercise_ids:
        exercises_by_id = {
            exercise.id: exercise
            for exercise in db.execute(
                select(Exercise).where(Exercise.id.in_(exercise_ids))
            ).scalars().all()
        }

    current_block_summary = summarize_training_block(current_sessions)
    previous_block_summary = summarize_training_block(previous_sessions) if previous_mesocycle else None
    comparison_to_previous = None
    if previous_block_summary is not None:
        comparison_to_previous = compare_training_blocks(
            current_block_summary,
            previous_block_summary,
        )

    session_efforts = build_session_effort_summaries(current_sessions)
    deload_suggestion = detect_deload_suggestion(session_efforts)

    current_exercise_summaries = build_exercise_block_summaries(
        current_sessions,
        default_formula=normalized_formula,
    )
    previous_exercise_summaries = build_exercise_block_summaries(
        previous_sessions,
        default_formula=normalized_formula,
    ) if previous_sessions else {}

    exercise_comparisons = []
    for exercise_id in sorted(
        set(current_exercise_summaries) | set(previous_exercise_summaries),
        key=lambda item: (
            (exercises_by_id[item].name.lower() if item in exercises_by_id else item),
            item,
        ),
    ):
        current_summary = current_exercise_summaries.get(exercise_id)
        previous_summary = previous_exercise_summaries.get(exercise_id)
        exercise = exercises_by_id.get(exercise_id)
        exercise_comparisons.append(
            ExerciseBlockComparisonResponse(
                exercise_id=exercise_id,
                exercise_name=exercise.name if exercise is not None else exercise_id,
                current_completed_sets=current_summary.completed_sets if current_summary else 0,
                previous_completed_sets=previous_summary.completed_sets if previous_summary else 0,
                completed_sets_delta=(
                    (current_summary.completed_sets if current_summary else 0)
                    - (previous_summary.completed_sets if previous_summary else 0)
                ),
                current_total_volume_load=current_summary.total_volume_load if current_summary else 0.0,
                previous_total_volume_load=previous_summary.total_volume_load if previous_summary else 0.0,
                total_volume_load_delta=round(
                    (current_summary.total_volume_load if current_summary else 0.0)
                    - (previous_summary.total_volume_load if previous_summary else 0.0),
                    2,
                ),
                current_best_e1rm=current_summary.best_e1rm if current_summary else None,
                previous_best_e1rm=previous_summary.best_e1rm if previous_summary else None,
                best_e1rm_delta=_calculate_delta(
                    current_summary.best_e1rm if current_summary else None,
                    previous_summary.best_e1rm if previous_summary else None,
                ),
            )
        )

    weeks_in_scope = _resolve_mesocycle_weeks(mesocycle, current_sessions)
    muscle_groups = [
        muscle_group
        for session in current_sessions
        for exercise_set in session.sets
        if exercise_set.set_type.lower() != "warmup"
        for muscle_group in [_resolve_muscle_group(exercises_by_id.get(exercise_set.exercise_id))]
        if muscle_group is not None
    ]
    muscle_balance = calculate_muscle_group_balance(
        muscle_groups,
        weeks_in_scope=weeks_in_scope,
    )

    return MesocycleAnalyticsResponse(
        mesocycle=MesocycleResponse.model_validate(mesocycle),
        previous_mesocycle=MesocycleResponse.model_validate(previous_mesocycle) if previous_mesocycle else None,
        current_block_summary=_serialize_training_block_summary(current_block_summary),
        previous_block_summary=(
            _serialize_training_block_summary(previous_block_summary)
            if previous_block_summary is not None
            else None
        ),
        comparison_to_previous=(
            TrainingBlockDeltaResponse(
                completed_sessions_delta=comparison_to_previous.completed_sessions_delta,
                total_sets_delta=comparison_to_previous.total_sets_delta,
                distinct_exercises_delta=comparison_to_previous.distinct_exercises_delta,
                total_volume_load_delta=comparison_to_previous.total_volume_load_delta,
                average_session_volume_load_delta=comparison_to_previous.average_session_volume_load_delta,
                average_session_rpe_delta=comparison_to_previous.average_session_rpe_delta,
            )
            if comparison_to_previous is not None
            else None
        ),
        deload_suggestion=DeloadSuggestionResponse(
            is_recommended=deload_suggestion.is_recommended,
            threshold=deload_suggestion.threshold,
            minimum_consecutive_weeks=deload_suggestion.minimum_consecutive_weeks,
            current_consecutive_high_weeks=deload_suggestion.current_consecutive_high_weeks,
            longest_consecutive_high_weeks=deload_suggestion.longest_consecutive_high_weeks,
            weekly_average_rpe=[
                WeeklyEffortResponse(
                    week_start=item.week_start,
                    week_end=item.week_end,
                    average_rpe=item.average_rpe,
                    session_count=item.session_count,
                    exceeded_threshold=item.exceeded_threshold,
                )
                for item in deload_suggestion.weekly_average_rpe
            ],
        ),
        exercise_comparisons=exercise_comparisons,
        muscle_balance=MuscleBalanceReportResponse(
            weeks_in_scope=weeks_in_scope,
            items=[
                MuscleGroupBalanceItemResponse(
                    muscle_group=item.muscle_group,
                    completed_sets=item.completed_sets,
                    average_weekly_sets=item.average_weekly_sets,
                    minimum_weekly_sets=item.minimum_weekly_sets,
                    difference_vs_minimum=item.difference_vs_minimum,
                    meets_minimum=item.meets_minimum,
                )
                for item in muscle_balance
            ],
        ),
    )


@router.get("/{mesocycle_id}", response_model=MesocycleDetailResponse)
async def get_mesocycle(
    mesocycle_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> MesocycleDetailResponse:
    mesocycle = _get_mesocycle(
        db,
        current_user.id,
        mesocycle_id,
        with_sessions=True,
    )
    if mesocycle is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Mesocycle not found",
        )

    return MesocycleDetailResponse.model_validate(mesocycle)


@router.patch("/{mesocycle_id}", response_model=MesocycleResponse)
async def update_mesocycle(
    mesocycle_id: int,
    payload: MesocycleUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> MesocycleResponse:
    mesocycle = _get_mesocycle(db, current_user.id, mesocycle_id)
    if mesocycle is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Mesocycle not found",
        )

    updates = payload.model_dump(exclude_unset=True)
    if not updates:
        return MesocycleResponse.model_validate(mesocycle)

    _validate_mesocycle_payload(
        goal=updates.get("goal", mesocycle.goal),
        started_on=mesocycle.started_on,
        ended_on=updates.get("ended_on", mesocycle.ended_on),
        weeks=updates.get("weeks", mesocycle.weeks),
    )

    for field, value in updates.items():
        setattr(mesocycle, field, value)

    db.commit()
    db.refresh(mesocycle)

    return MesocycleResponse.model_validate(mesocycle)


@router.delete("/{mesocycle_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_mesocycle(
    mesocycle_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Response:
    mesocycle = _get_mesocycle(db, current_user.id, mesocycle_id)
    if mesocycle is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Mesocycle not found",
        )

    db.delete(mesocycle)
    db.commit()

    return Response(status_code=status.HTTP_204_NO_CONTENT)
