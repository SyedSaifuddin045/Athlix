from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from math import ceil

from app.models.workout import ExerciseSet, WorkoutSession

SUPPORTED_E1RM_FORMULAS = (
    "epley",
    "brzycki",
    "lombardi",
    "oconner",
)
DEFAULT_E1RM_FORMULA = "epley"
DELOAD_RPE_THRESHOLD = 8.5
DELOAD_MIN_CONSECUTIVE_WEEKS = 2
DEFAULT_MINIMUM_WEEKLY_SETS = 6.0
EVIDENCE_BASED_MINIMUM_WEEKLY_SETS = {
    "abductors": 4.0,
    "abs": 4.0,
    "adductors": 4.0,
    "biceps": 6.0,
    "calves": 6.0,
    "cardiovascular system": 4.0,
    "chest": 6.0,
    "delts": 6.0,
    "forearms": 4.0,
    "glutes": 6.0,
    "hamstrings": 6.0,
    "lats": 6.0,
    "lower arms": 4.0,
    "lower back": 4.0,
    "middle back": 6.0,
    "neck": 4.0,
    "pectorals": 6.0,
    "quads": 6.0,
    "quads and glutes": 6.0,
    "rear delts": 6.0,
    "shoulders": 6.0,
    "spine": 4.0,
    "traps": 6.0,
    "triceps": 6.0,
    "upper arms": 6.0,
    "upper back": 6.0,
    "upper legs": 6.0,
    "waist": 4.0,
}


@dataclass
class SessionExerciseSummary:
    session_id: int
    performed_at: datetime
    volume_load: float
    best_set_id: int | None
    best_weight_kg: float | None
    best_reps: int | None
    default_e1rm: float | None
    e1rm_formulas: dict[str, float | None]


@dataclass
class WeeklyVolumeSummary:
    week_start: date
    week_end: date
    volume_load: float


@dataclass
class ProgressiveOverloadSummary:
    current_session_id: int
    previous_session_id: int
    performed_at: datetime
    current_volume_load: float
    previous_volume_load: float
    volume_load_delta: float
    current_best_weight_kg: float | None
    previous_best_weight_kg: float | None
    best_weight_delta: float | None
    current_default_e1rm: float | None
    previous_default_e1rm: float | None
    default_e1rm_delta: float | None
    improved_metrics: list[str]


@dataclass
class WorkoutStreaks:
    current_daily_streak: int
    longest_daily_streak: int
    current_weekly_streak: int
    longest_weekly_streak: int


@dataclass
class SessionEffortSummary:
    session_id: int
    performed_at: datetime
    average_rpe: float | None


@dataclass
class WeeklyEffortSummary:
    week_start: date
    week_end: date
    average_rpe: float
    session_count: int
    exceeded_threshold: bool


@dataclass
class DeloadSuggestion:
    is_recommended: bool
    threshold: float
    minimum_consecutive_weeks: int
    current_consecutive_high_weeks: int
    longest_consecutive_high_weeks: int
    weekly_average_rpe: list[WeeklyEffortSummary]


@dataclass
class TrainingBlockSummary:
    completed_sessions: int
    total_sets: int
    distinct_exercises: int
    total_volume_load: float
    average_session_volume_load: float
    average_session_rpe: float | None


@dataclass
class TrainingBlockDelta:
    completed_sessions_delta: int
    total_sets_delta: int
    distinct_exercises_delta: int
    total_volume_load_delta: float
    average_session_volume_load_delta: float
    average_session_rpe_delta: float | None


@dataclass
class ExerciseBlockSummary:
    exercise_id: str
    completed_sets: int
    total_volume_load: float
    best_weight_kg: float | None
    best_reps: int | None
    best_e1rm: float | None


@dataclass
class MuscleGroupBalanceSummary:
    muscle_group: str
    completed_sets: int
    average_weekly_sets: float
    minimum_weekly_sets: float
    difference_vs_minimum: float
    meets_minimum: bool


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _performed_at_for_session(session: WorkoutSession, fallback: datetime | None = None) -> datetime:
    if session.finished_at is not None:
        return session.finished_at
    if session.started_at is not None:
        return session.started_at
    if fallback is not None:
        return fallback
    return _utcnow()


def _calculate_delta(current: float | None, previous: float | None) -> float | None:
    if current is not None and previous is not None:
        return round(current - previous, 2)
    if current is not None:
        return round(current, 2)
    return None


def estimate_weeks_in_range(started_on: date, ended_on: date | None) -> int:
    range_end = ended_on or started_on
    total_days = (range_end - started_on).days + 1
    return max(1, ceil(total_days / 7))


def calculate_e1rm(
    weight_kg: float | None,
    reps: int | None,
    formula: str = DEFAULT_E1RM_FORMULA,
) -> float | None:
    if weight_kg is None or reps is None or weight_kg <= 0 or reps <= 0:
        return None

    normalized_formula = formula.lower()
    if normalized_formula == "epley":
        value = weight_kg * (1 + reps / 30)
    elif normalized_formula == "brzycki":
        if reps >= 37:
            return None
        value = weight_kg * 36 / (37 - reps)
    elif normalized_formula == "lombardi":
        value = weight_kg * (reps ** 0.10)
    elif normalized_formula == "oconner":
        value = weight_kg * (1 + 0.025 * reps)
    else:
        raise ValueError(f"Unsupported e1RM formula: {formula}")

    return round(value, 2)


def calculate_e1rm_all(weight_kg: float | None, reps: int | None) -> dict[str, float | None]:
    return {
        formula: calculate_e1rm(weight_kg, reps, formula)
        for formula in SUPPORTED_E1RM_FORMULAS
    }


def calculate_set_volume_load(weight_kg: float | None, reps: int | None) -> float:
    if weight_kg is None or reps is None or weight_kg <= 0 or reps <= 0:
        return 0.0
    return round(weight_kg * reps, 2)


def calculate_session_volume_load(exercise_sets: list[ExerciseSet] | tuple[ExerciseSet, ...]) -> float:
    return round(
        sum(calculate_set_volume_load(exercise_set.weight_kg, exercise_set.reps) for exercise_set in exercise_sets),
        2,
    )


def calculate_session_average_rpe(
    exercise_sets: list[ExerciseSet] | tuple[ExerciseSet, ...],
    *,
    perceived_exertion: int | float | None = None,
) -> float | None:
    set_rpes = [
        float(exercise_set.rpe)
        for exercise_set in exercise_sets
        if exercise_set.rpe is not None and float(exercise_set.rpe) > 0
    ]
    if set_rpes:
        return round(sum(set_rpes) / len(set_rpes), 2)
    if perceived_exertion is not None and float(perceived_exertion) > 0:
        return round(float(perceived_exertion), 2)
    return None


def build_session_exercise_summaries(
    rows: list[tuple[ExerciseSet, WorkoutSession]],
    *,
    default_formula: str = DEFAULT_E1RM_FORMULA,
) -> list[SessionExerciseSummary]:
    summaries: dict[int, SessionExerciseSummary] = {}
    ranking_keys: dict[int, tuple[float, float, int, datetime, int]] = {}

    for exercise_set, session in rows:
        performed_at = session.finished_at or session.started_at or exercise_set.logged_at or _utcnow()
        summary = summaries.get(session.id)
        if summary is None:
            summary = SessionExerciseSummary(
                session_id=session.id,
                performed_at=performed_at,
                volume_load=0.0,
                best_set_id=None,
                best_weight_kg=None,
                best_reps=None,
                default_e1rm=None,
                e1rm_formulas={formula: None for formula in SUPPORTED_E1RM_FORMULAS},
            )
            summaries[session.id] = summary
            ranking_keys[session.id] = (-1.0, -1.0, -1, performed_at, -1)

        summary.volume_load = round(
            summary.volume_load + calculate_set_volume_load(exercise_set.weight_kg, exercise_set.reps),
            2,
        )

        formulas = calculate_e1rm_all(exercise_set.weight_kg, exercise_set.reps)
        default_e1rm = formulas[default_formula]
        candidate_key = (
            default_e1rm if default_e1rm is not None else -1.0,
            float(exercise_set.weight_kg) if exercise_set.weight_kg is not None else -1.0,
            exercise_set.reps if exercise_set.reps is not None else -1,
            exercise_set.logged_at or performed_at,
            exercise_set.id,
        )
        if candidate_key > ranking_keys[session.id]:
            ranking_keys[session.id] = candidate_key
            summary.best_set_id = exercise_set.id
            summary.best_weight_kg = float(exercise_set.weight_kg) if exercise_set.weight_kg is not None else None
            summary.best_reps = exercise_set.reps
            summary.default_e1rm = default_e1rm
            summary.e1rm_formulas = formulas

    return sorted(
        summaries.values(),
        key=lambda summary: (summary.performed_at, summary.session_id),
    )


def calculate_weekly_volume_summaries(
    session_summaries: list[SessionExerciseSummary] | tuple[SessionExerciseSummary, ...],
) -> list[WeeklyVolumeSummary]:
    volumes_by_week: dict[date, float] = {}

    for summary in session_summaries:
        week_start = summary.performed_at.date() - timedelta(days=summary.performed_at.weekday())
        volumes_by_week[week_start] = round(volumes_by_week.get(week_start, 0.0) + summary.volume_load, 2)

    return [
        WeeklyVolumeSummary(
            week_start=week_start,
            week_end=week_start + timedelta(days=6),
            volume_load=volume_load,
        )
        for week_start, volume_load in sorted(volumes_by_week.items())
    ]


def build_session_effort_summaries(
    sessions: list[WorkoutSession] | tuple[WorkoutSession, ...],
) -> list[SessionEffortSummary]:
    summaries = [
        SessionEffortSummary(
            session_id=session.id,
            performed_at=_performed_at_for_session(session),
            average_rpe=calculate_session_average_rpe(
                list(session.sets),
                perceived_exertion=session.perceived_exertion,
            ),
        )
        for session in sessions
    ]
    return sorted(summaries, key=lambda summary: (summary.performed_at, summary.session_id))


def calculate_weekly_effort_summaries(
    session_efforts: list[SessionEffortSummary] | tuple[SessionEffortSummary, ...],
    *,
    threshold: float = DELOAD_RPE_THRESHOLD,
) -> list[WeeklyEffortSummary]:
    effort_by_week: dict[date, list[float]] = {}

    for summary in session_efforts:
        if summary.average_rpe is None:
            continue
        week_start = summary.performed_at.date() - timedelta(days=summary.performed_at.weekday())
        effort_by_week.setdefault(week_start, []).append(summary.average_rpe)

    return [
        WeeklyEffortSummary(
            week_start=week_start,
            week_end=week_start + timedelta(days=6),
            average_rpe=round(sum(values) / len(values), 2),
            session_count=len(values),
            exceeded_threshold=round(sum(values) / len(values), 2) > threshold,
        )
        for week_start, values in sorted(effort_by_week.items())
    ]


def detect_deload_suggestion(
    session_efforts: list[SessionEffortSummary] | tuple[SessionEffortSummary, ...],
    *,
    threshold: float = DELOAD_RPE_THRESHOLD,
    minimum_consecutive_weeks: int = DELOAD_MIN_CONSECUTIVE_WEEKS,
) -> DeloadSuggestion:
    weekly_efforts = calculate_weekly_effort_summaries(
        session_efforts,
        threshold=threshold,
    )

    longest_streak = 0
    running_streak = 0
    for weekly_effort in weekly_efforts:
        if weekly_effort.exceeded_threshold:
            running_streak += 1
            longest_streak = max(longest_streak, running_streak)
        else:
            running_streak = 0

    current_streak = 0
    for weekly_effort in reversed(weekly_efforts):
        if not weekly_effort.exceeded_threshold:
            break
        current_streak += 1

    return DeloadSuggestion(
        is_recommended=current_streak >= minimum_consecutive_weeks,
        threshold=threshold,
        minimum_consecutive_weeks=minimum_consecutive_weeks,
        current_consecutive_high_weeks=current_streak,
        longest_consecutive_high_weeks=longest_streak,
        weekly_average_rpe=weekly_efforts,
    )


def detect_progressive_overload(
    session_summaries: list[SessionExerciseSummary] | tuple[SessionExerciseSummary, ...],
) -> list[ProgressiveOverloadSummary]:
    overload_points: list[ProgressiveOverloadSummary] = []

    for previous, current in zip(session_summaries, session_summaries[1:]):
        improved_metrics: list[str] = []
        volume_load_delta = round(current.volume_load - previous.volume_load, 2)
        if volume_load_delta > 0:
            improved_metrics.append("volume_load")

        best_weight_delta = None
        if current.best_weight_kg is not None and previous.best_weight_kg is not None:
            best_weight_delta = round(current.best_weight_kg - previous.best_weight_kg, 2)
        elif current.best_weight_kg is not None:
            best_weight_delta = round(current.best_weight_kg, 2)
        if best_weight_delta is not None and best_weight_delta > 0:
            improved_metrics.append("best_weight")

        default_e1rm_delta = None
        if current.default_e1rm is not None and previous.default_e1rm is not None:
            default_e1rm_delta = round(current.default_e1rm - previous.default_e1rm, 2)
        elif current.default_e1rm is not None:
            default_e1rm_delta = round(current.default_e1rm, 2)
        if default_e1rm_delta is not None and default_e1rm_delta > 0:
            improved_metrics.append("estimated_1rm")

        overload_points.append(
            ProgressiveOverloadSummary(
                current_session_id=current.session_id,
                previous_session_id=previous.session_id,
                performed_at=current.performed_at,
                current_volume_load=current.volume_load,
                previous_volume_load=previous.volume_load,
                volume_load_delta=volume_load_delta,
                current_best_weight_kg=current.best_weight_kg,
                previous_best_weight_kg=previous.best_weight_kg,
                best_weight_delta=best_weight_delta,
                current_default_e1rm=current.default_e1rm,
                previous_default_e1rm=previous.default_e1rm,
                default_e1rm_delta=default_e1rm_delta,
                improved_metrics=improved_metrics,
            )
        )

    return overload_points


def summarize_training_block(
    sessions: list[WorkoutSession] | tuple[WorkoutSession, ...],
) -> TrainingBlockSummary:
    if not sessions:
        return TrainingBlockSummary(
            completed_sessions=0,
            total_sets=0,
            distinct_exercises=0,
            total_volume_load=0.0,
            average_session_volume_load=0.0,
            average_session_rpe=None,
        )

    total_sets = 0
    exercise_ids: set[str] = set()
    total_volume_load = 0.0
    session_rpes: list[float] = []

    for session in sessions:
        session_sets = list(session.sets)
        total_sets += len(session_sets)
        exercise_ids.update(
            exercise_set.exercise_id
            for exercise_set in session_sets
            if exercise_set.exercise_id
        )
        total_volume_load = round(
            total_volume_load + calculate_session_volume_load(session_sets),
            2,
        )
        session_average_rpe = calculate_session_average_rpe(
            session_sets,
            perceived_exertion=session.perceived_exertion,
        )
        if session_average_rpe is not None:
            session_rpes.append(session_average_rpe)

    average_session_rpe = None
    if session_rpes:
        average_session_rpe = round(sum(session_rpes) / len(session_rpes), 2)

    return TrainingBlockSummary(
        completed_sessions=len(sessions),
        total_sets=total_sets,
        distinct_exercises=len(exercise_ids),
        total_volume_load=round(total_volume_load, 2),
        average_session_volume_load=round(total_volume_load / len(sessions), 2),
        average_session_rpe=average_session_rpe,
    )


def compare_training_blocks(
    current_block: TrainingBlockSummary,
    previous_block: TrainingBlockSummary,
) -> TrainingBlockDelta:
    return TrainingBlockDelta(
        completed_sessions_delta=current_block.completed_sessions - previous_block.completed_sessions,
        total_sets_delta=current_block.total_sets - previous_block.total_sets,
        distinct_exercises_delta=current_block.distinct_exercises - previous_block.distinct_exercises,
        total_volume_load_delta=round(
            current_block.total_volume_load - previous_block.total_volume_load,
            2,
        ),
        average_session_volume_load_delta=round(
            current_block.average_session_volume_load - previous_block.average_session_volume_load,
            2,
        ),
        average_session_rpe_delta=_calculate_delta(
            current_block.average_session_rpe,
            previous_block.average_session_rpe,
        ),
    )


def build_exercise_block_summaries(
    sessions: list[WorkoutSession] | tuple[WorkoutSession, ...],
    *,
    default_formula: str = DEFAULT_E1RM_FORMULA,
) -> dict[str, ExerciseBlockSummary]:
    summaries: dict[str, ExerciseBlockSummary] = {}
    ranking_keys: dict[str, tuple[float, float, int, datetime, int]] = {}

    for session in sessions:
        performed_at = _performed_at_for_session(session)
        for exercise_set in session.sets:
            summary = summaries.get(exercise_set.exercise_id)
            if summary is None:
                summary = ExerciseBlockSummary(
                    exercise_id=exercise_set.exercise_id,
                    completed_sets=0,
                    total_volume_load=0.0,
                    best_weight_kg=None,
                    best_reps=None,
                    best_e1rm=None,
                )
                summaries[exercise_set.exercise_id] = summary
                ranking_keys[exercise_set.exercise_id] = (-1.0, -1.0, -1, performed_at, -1)

            summary.completed_sets += 1
            summary.total_volume_load = round(
                summary.total_volume_load
                + calculate_set_volume_load(exercise_set.weight_kg, exercise_set.reps),
                2,
            )

            default_e1rm = calculate_e1rm(
                exercise_set.weight_kg,
                exercise_set.reps,
                default_formula,
            )
            candidate_key = (
                default_e1rm if default_e1rm is not None else -1.0,
                float(exercise_set.weight_kg) if exercise_set.weight_kg is not None else -1.0,
                exercise_set.reps if exercise_set.reps is not None else -1,
                exercise_set.logged_at or performed_at,
                exercise_set.id,
            )
            if candidate_key > ranking_keys[exercise_set.exercise_id]:
                ranking_keys[exercise_set.exercise_id] = candidate_key
                summary.best_weight_kg = float(exercise_set.weight_kg) if exercise_set.weight_kg is not None else None
                summary.best_reps = exercise_set.reps
                summary.best_e1rm = default_e1rm

    return summaries


def calculate_muscle_group_balance(
    muscle_groups: list[str] | tuple[str, ...],
    *,
    weeks_in_scope: int,
    minimum_weekly_sets: dict[str, float] | None = None,
) -> list[MuscleGroupBalanceSummary]:
    normalized_weeks = max(1, weeks_in_scope)
    thresholds = minimum_weekly_sets or EVIDENCE_BASED_MINIMUM_WEEKLY_SETS
    counts: dict[str, int] = {}

    for muscle_group in muscle_groups:
        normalized_group = muscle_group.strip().lower()
        if not normalized_group:
            continue
        counts[normalized_group] = counts.get(normalized_group, 0) + 1

    summaries = [
        MuscleGroupBalanceSummary(
            muscle_group=muscle_group,
            completed_sets=completed_sets,
            average_weekly_sets=round(completed_sets / normalized_weeks, 2),
            minimum_weekly_sets=thresholds.get(muscle_group, DEFAULT_MINIMUM_WEEKLY_SETS),
            difference_vs_minimum=round(
                completed_sets / normalized_weeks - thresholds.get(muscle_group, DEFAULT_MINIMUM_WEEKLY_SETS),
                2,
            ),
            meets_minimum=(completed_sets / normalized_weeks) >= thresholds.get(
                muscle_group,
                DEFAULT_MINIMUM_WEEKLY_SETS,
            ),
        )
        for muscle_group, completed_sets in counts.items()
    ]
    return sorted(summaries, key=lambda item: (item.meets_minimum, item.muscle_group))


def calculate_workout_streaks(
    session_datetimes: list[datetime] | tuple[datetime, ...],
    *,
    reference_date: date | None = None,
) -> WorkoutStreaks:
    if reference_date is None:
        reference_date = datetime.now(timezone.utc).date()

    session_dates = sorted({session_datetime.date() for session_datetime in session_datetimes})
    if not session_dates:
        return WorkoutStreaks(
            current_daily_streak=0,
            longest_daily_streak=0,
            current_weekly_streak=0,
            longest_weekly_streak=0,
        )

    longest_daily_streak = 0
    running_daily_streak = 0
    previous_date: date | None = None
    for session_date in session_dates:
        if previous_date is not None and session_date == previous_date + timedelta(days=1):
            running_daily_streak += 1
        else:
            running_daily_streak = 1
        longest_daily_streak = max(longest_daily_streak, running_daily_streak)
        previous_date = session_date

    session_date_set = set(session_dates)
    current_daily_streak = 0
    cursor = reference_date
    while cursor in session_date_set:
        current_daily_streak += 1
        cursor -= timedelta(days=1)

    week_starts = sorted({session_date - timedelta(days=session_date.weekday()) for session_date in session_dates})
    longest_weekly_streak = 0
    running_weekly_streak = 0
    previous_week_start: date | None = None
    for week_start in week_starts:
        if previous_week_start is not None and week_start == previous_week_start + timedelta(days=7):
            running_weekly_streak += 1
        else:
            running_weekly_streak = 1
        longest_weekly_streak = max(longest_weekly_streak, running_weekly_streak)
        previous_week_start = week_start

    week_start_set = set(week_starts)
    reference_week_start = reference_date - timedelta(days=reference_date.weekday())
    current_weekly_streak = 0
    cursor_week = reference_week_start
    while cursor_week in week_start_set:
        current_weekly_streak += 1
        cursor_week -= timedelta(days=7)

    return WorkoutStreaks(
        current_daily_streak=current_daily_streak,
        longest_daily_streak=longest_daily_streak,
        current_weekly_streak=current_weekly_streak,
        longest_weekly_streak=longest_weekly_streak,
    )
