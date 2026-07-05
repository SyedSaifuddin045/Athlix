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
