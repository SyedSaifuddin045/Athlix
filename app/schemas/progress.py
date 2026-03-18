from datetime import date, datetime

from .base_schema import BaseSchema


class E1RMFormulaResponse(BaseSchema):
    epley: float | None
    brzycki: float | None
    lombardi: float | None
    oconner: float | None


class ExerciseProgressPointResponse(BaseSchema):
    session_id: int
    performed_at: datetime
    best_set_id: int | None
    weight_kg: float | None
    reps: int | None
    default_e1rm: float | None
    formulas: E1RMFormulaResponse
    volume_load: float


class WeeklyVolumeProgressPointResponse(BaseSchema):
    week_start: date
    week_end: date
    volume_load: float


class ProgressiveOverloadResponse(BaseSchema):
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


class WorkoutStreaksResponse(BaseSchema):
    current_daily_streak: int
    longest_daily_streak: int
    current_weekly_streak: int
    longest_weekly_streak: int


class ExerciseProgressResponse(BaseSchema):
    exercise_id: str
    exercise_name: str
    default_formula: str
    e1rm_history: list[ExerciseProgressPointResponse]
    volume_history: list[ExerciseProgressPointResponse]
    weekly_volume_history: list[WeeklyVolumeProgressPointResponse]
    progressive_overload: list[ProgressiveOverloadResponse]
    workout_streaks: WorkoutStreaksResponse
