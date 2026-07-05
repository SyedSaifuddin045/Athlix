from datetime import datetime
from app.schemas.base_schema import BaseSchema


class DeviceRegisterRequest(BaseSchema):
    platform: str  # "android" or "ios"
    push_token: str
    device_name: str | None = None
    app_version: str | None = None


class DeviceUnregisterRequest(BaseSchema):
    push_token: str


class DeviceResponse(BaseSchema):
    id: int
    platform: str
    push_token: str
    device_name: str | None
    app_version: str | None
    last_seen: datetime | None
    created_at: datetime


class NotificationSettingsResponse(BaseSchema):
    morning_motivation_enabled: bool
    inactivity_nudge_enabled: bool
    milestone_enabled: bool
    timezone: str
    preferred_send_hour: int
    inactivity_threshold_hours: int
    detected_timezone: str | None = None
    typical_workout_hour: int | None = None
    typical_workout_days: list[int] | None = None
    last_milestone_workout_count: int
    created_at: datetime
    updated_at: datetime


class NotificationSettingsUpdate(BaseSchema):
    morning_motivation_enabled: bool | None = None
    inactivity_nudge_enabled: bool | None = None
    milestone_enabled: bool | None = None
    timezone: str | None = None
    preferred_send_hour: int | None = None
    inactivity_threshold_hours: int | None = None


class NotificationSettingsDetectRequest(BaseSchema):
    timezone: str  # IANA timezone string from device
    typical_workout_hour: int | None = None
    typical_workout_days: list[int] | None = None
