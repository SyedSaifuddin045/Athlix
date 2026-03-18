from datetime import date, datetime, timezone

from app.core.analytics import (
    build_session_exercise_summaries,
    build_session_effort_summaries,
    build_exercise_block_summaries,
    calculate_muscle_group_balance,
    calculate_e1rm,
    calculate_e1rm_all,
    calculate_session_volume_load,
    calculate_session_average_rpe,
    calculate_set_volume_load,
    calculate_weekly_volume_summaries,
    calculate_workout_streaks,
    compare_training_blocks,
    detect_deload_suggestion,
    detect_progressive_overload,
    summarize_training_block,
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
    rpe: float | None = None,
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
        rpe=rpe,
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


def test_session_effort_and_deload_detection_use_set_rpe_first():
    first_session = make_session(1, "2026-03-03T06:00:00Z")
    second_session = make_session(2, "2026-03-10T06:00:00Z")
    third_session = make_session(3, "2026-03-17T06:00:00Z")

    first_session.sets = [make_set(1, 1, "bench", 1, 5, 100, 8.0)]
    second_session.sets = [make_set(2, 2, "bench", 1, 5, 102.5, 8.7)]
    third_session.sets = [make_set(3, 3, "bench", 1, 5, 105, 8.9)]

    efforts = build_session_effort_summaries([first_session, second_session, third_session])
    suggestion = detect_deload_suggestion(efforts)

    assert calculate_session_average_rpe(first_session.sets) == 8.0
    assert [item.average_rpe for item in suggestion.weekly_average_rpe] == [8.0, 8.7, 8.9]
    assert suggestion.current_consecutive_high_weeks == 2
    assert suggestion.longest_consecutive_high_weeks == 2
    assert suggestion.is_recommended is True


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


def test_training_block_comparison_and_muscle_balance_helpers():
    previous_session = make_session(1, "2026-02-03T06:00:00Z")
    current_first_session = make_session(2, "2026-03-03T06:00:00Z")
    current_second_session = make_session(3, "2026-03-10T06:00:00Z")

    previous_session.sets = [
        make_set(1, 1, "bench", 1, 5, 100, 8.0),
        make_set(2, 1, "squat", 2, 5, 140, 8.2),
    ]
    current_first_session.sets = [
        make_set(3, 2, "bench", 1, 5, 105, 8.6),
        make_set(4, 2, "squat", 2, 5, 145, 8.7),
    ]
    current_second_session.sets = [
        make_set(5, 3, "bench", 1, 5, 110, 8.9),
    ]

    previous_block = summarize_training_block([previous_session])
    current_block = summarize_training_block([current_first_session, current_second_session])
    delta = compare_training_blocks(current_block, previous_block)
    exercise_summaries = build_exercise_block_summaries(
        [current_first_session, current_second_session],
        default_formula="epley",
    )
    muscle_balance = calculate_muscle_group_balance(
        ["pectorals", "pectorals", "quads"],
        weeks_in_scope=4,
    )

    assert current_block.completed_sessions == 2
    assert current_block.total_volume_load == 1800
    assert delta.total_volume_load_delta == 600
    assert exercise_summaries["bench"].best_e1rm == 128.33
    assert exercise_summaries["bench"].completed_sets == 2
    assert muscle_balance[0].muscle_group == "pectorals"
    assert muscle_balance[0].average_weekly_sets == 0.5
    assert muscle_balance[0].meets_minimum is False


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
