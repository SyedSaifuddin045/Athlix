from datetime import date, datetime, timezone

from app.core.analytics import (
    build_session_exercise_summaries,
    calculate_e1rm,
    calculate_e1rm_all,
    calculate_session_volume_load,
    calculate_set_volume_load,
    calculate_weekly_volume_summaries,
    calculate_workout_streaks,
    detect_progressive_overload,
)
from app.models.workout import ExerciseSet, WorkoutSession


def make_session(session_id: int, started_at: str, finished_at: str | None = None) -> WorkoutSession:
    return WorkoutSession(
        id=session_id,
        user_id=1,
        template_id=None,
        mesocycle_id=None,
        name=f"Session {session_id}",
        started_at=datetime.fromisoformat(started_at.replace("Z", "+00:00")),
        finished_at=datetime.fromisoformat(finished_at.replace("Z", "+00:00")) if finished_at else None,
        perceived_exertion=None,
        mood=None,
        location=None,
        notes=None,
        is_completed=True,
    )


def make_set(
    set_id: int,
    session_id: int,
    exercise_id: str,
    set_number: int,
    reps: int | None,
    weight_kg: float | None,
) -> ExerciseSet:
    return ExerciseSet(
        id=set_id,
        session_id=session_id,
        exercise_id=exercise_id,
        set_number=set_number,
        set_type="working",
        reps=reps,
        weight_kg=weight_kg,
        duration_sec=None,
        distance_m=None,
        rpe=None,
        is_pr=False,
        notes=None,
        logged_at=datetime(2026, 3, 18, 6, set_number, tzinfo=timezone.utc),
    )


def test_e1rm_calculator_supports_all_formulas():
    values = calculate_e1rm_all(100, 5)

    assert calculate_e1rm(100, 5, "epley") == 116.67
    assert values["brzycki"] == 112.5
    assert values["lombardi"] == 117.46
    assert values["oconner"] == 112.5


def test_volume_load_helpers_aggregate_sets_and_weeks():
    first_session = make_session(1, "2026-03-10T06:00:00Z")
    second_session = make_session(2, "2026-03-17T06:00:00Z")
    first_set = make_set(1, 1, "bench", 1, 5, 100)
    second_set = make_set(2, 1, "bench", 2, 8, 90)
    third_set = make_set(3, 2, "bench", 1, 5, 110)

    assert calculate_set_volume_load(100, 5) == 500
    assert calculate_session_volume_load([first_set, second_set]) == 1220

    summaries = build_session_exercise_summaries(
        [
            (first_set, first_session),
            (second_set, first_session),
            (third_set, second_session),
        ]
    )
    weekly = calculate_weekly_volume_summaries(summaries)

    assert [summary.volume_load for summary in summaries] == [1220, 550]
    assert [(item.week_start.isoformat(), item.volume_load) for item in weekly] == [
        ("2026-03-09", 1220),
        ("2026-03-16", 550),
    ]


def test_progressive_overload_detector_compares_consecutive_sessions():
    first_session = make_session(1, "2026-03-10T06:00:00Z")
    second_session = make_session(2, "2026-03-17T06:00:00Z")
    summaries = build_session_exercise_summaries(
        [
            (make_set(1, 1, "bench", 1, 5, 100), first_session),
            (make_set(2, 2, "bench", 1, 5, 110), second_session),
        ]
    )

    overload = detect_progressive_overload(summaries)

    assert len(overload) == 1
    point = overload[0]
    assert point.volume_load_delta == 50
    assert point.best_weight_delta == 10
    assert point.default_e1rm_delta == 11.66
    assert point.improved_metrics == ["volume_load", "best_weight", "estimated_1rm"]


def test_workout_streaks_calculate_current_and_longest_sequences():
    streaks = calculate_workout_streaks(
        [
            datetime(2026, 3, 10, tzinfo=timezone.utc),
            datetime(2026, 3, 11, tzinfo=timezone.utc),
            datetime(2026, 3, 12, tzinfo=timezone.utc),
            datetime(2026, 3, 17, tzinfo=timezone.utc),
            datetime(2026, 3, 18, tzinfo=timezone.utc),
            datetime(2026, 3, 24, tzinfo=timezone.utc),
        ],
        reference_date=date(2026, 3, 18),
    )

    assert streaks.current_daily_streak == 2
    assert streaks.longest_daily_streak == 3
    assert streaks.current_weekly_streak == 2
    assert streaks.longest_weekly_streak == 3
