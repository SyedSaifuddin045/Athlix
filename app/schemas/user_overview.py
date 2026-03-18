from .base_schema import BaseSchema
from .body_weight import BodyWeightLogResponse
from .mesocycle import MesocycleResponse
from .personal_record import PersonalRecordResponse
from .progress import WorkoutStreaksResponse
from .user_profile import UserProfileResponse
from .user_schema import UserResponse
from .workout_session import WorkoutSessionResponse


class UserOverviewStatsResponse(BaseSchema):
    total_workout_templates: int
    total_sessions: int
    completed_sessions: int
    personal_record_count: int


class UserOverviewResponse(BaseSchema):
    user: UserResponse
    has_profile: bool
    profile: UserProfileResponse | None
    latest_body_weight_log: BodyWeightLogResponse | None
    active_mesocycle: MesocycleResponse | None
    latest_completed_session: WorkoutSessionResponse | None
    recent_personal_records: list[PersonalRecordResponse]
    workout_streaks: WorkoutStreaksResponse
    stats: UserOverviewStatsResponse
