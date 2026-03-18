from datetime import date

from .base_schema import BaseSchema
from .mesocycle import MesocycleResponse


class WeeklyEffortResponse(BaseSchema):
    week_start: date
    week_end: date
    average_rpe: float
    session_count: int
    exceeded_threshold: bool


class DeloadSuggestionResponse(BaseSchema):
    is_recommended: bool
    threshold: float
    minimum_consecutive_weeks: int
    current_consecutive_high_weeks: int
    longest_consecutive_high_weeks: int
    weekly_average_rpe: list[WeeklyEffortResponse]


class TrainingBlockSummaryResponse(BaseSchema):
    completed_sessions: int
    total_sets: int
    distinct_exercises: int
    total_volume_load: float
    average_session_volume_load: float
    average_session_rpe: float | None


class TrainingBlockDeltaResponse(BaseSchema):
    completed_sessions_delta: int
    total_sets_delta: int
    distinct_exercises_delta: int
    total_volume_load_delta: float
    average_session_volume_load_delta: float
    average_session_rpe_delta: float | None


class ExerciseBlockComparisonResponse(BaseSchema):
    exercise_id: str
    exercise_name: str
    current_completed_sets: int
    previous_completed_sets: int
    completed_sets_delta: int
    current_total_volume_load: float
    previous_total_volume_load: float
    total_volume_load_delta: float
    current_best_e1rm: float | None
    previous_best_e1rm: float | None
    best_e1rm_delta: float | None


class MuscleGroupBalanceItemResponse(BaseSchema):
    muscle_group: str
    completed_sets: int
    average_weekly_sets: float
    minimum_weekly_sets: float
    difference_vs_minimum: float
    meets_minimum: bool


class MuscleBalanceReportResponse(BaseSchema):
    weeks_in_scope: int
    items: list[MuscleGroupBalanceItemResponse]


class MesocycleAnalyticsResponse(BaseSchema):
    mesocycle: MesocycleResponse
    previous_mesocycle: MesocycleResponse | None
    current_block_summary: TrainingBlockSummaryResponse
    previous_block_summary: TrainingBlockSummaryResponse | None
    comparison_to_previous: TrainingBlockDeltaResponse | None
    deload_suggestion: DeloadSuggestionResponse
    exercise_comparisons: list[ExerciseBlockComparisonResponse]
    muscle_balance: MuscleBalanceReportResponse
