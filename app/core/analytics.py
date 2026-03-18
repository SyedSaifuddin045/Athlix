from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone

from app.models.workout import ExerciseSet, WorkoutSession

SUPPORTED_E1RM_FORMULAS = (
    "epley",
    "brzycki",
    "lombardi",
    "oconner",
)
DEFAULT_E1RM_FORMULA = "epley"


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


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


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
