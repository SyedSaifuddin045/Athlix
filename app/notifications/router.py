import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models.user import User
from app.notifications.repository import NotificationRepository
from app.notifications.schemas import (
    DeviceRegisterRequest,
    DeviceUnregisterRequest,
    DeviceResponse,
    NotificationSettingsResponse,
    NotificationSettingsUpdate,
    NotificationSettingsDetectRequest,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/devices", tags=["Notifications"])


def _get_repo(db: Session = Depends(get_db)) -> NotificationRepository:
    return NotificationRepository(db)


@router.post("/register", response_model=DeviceResponse, status_code=201)
async def register_device(
    payload: DeviceRegisterRequest,
    repo: NotificationRepository = Depends(_get_repo),
    current_user: User = Depends(get_current_user),
) -> DeviceResponse:
    device = repo.upsert_device(current_user.id, payload)
    logger.info("Device registered: user=%d platform=%s", current_user.id, payload.platform)
    return DeviceResponse.model_validate(device)


@router.post("/unregister", status_code=204)
async def unregister_device(
    payload: DeviceUnregisterRequest,
    repo: NotificationRepository = Depends(_get_repo),
    current_user: User = Depends(get_current_user),
) -> None:
    deleted = repo.delete_device_by_token(current_user.id, payload.push_token)
    if deleted:
        logger.info("Device unregistered: user=%d", current_user.id)
    return None


@router.get("", response_model=list[DeviceResponse])
async def list_devices(
    repo: NotificationRepository = Depends(_get_repo),
    current_user: User = Depends(get_current_user),
) -> list[DeviceResponse]:
    devices = repo.get_active_devices(current_user.id)
    return [DeviceResponse.model_validate(d) for d in devices]


@router.get("/settings", response_model=NotificationSettingsResponse)
async def get_notification_settings(
    repo: NotificationRepository = Depends(_get_repo),
    current_user: User = Depends(get_current_user),
) -> NotificationSettingsResponse:
    """Get current user's notification settings."""
    settings = repo.get_settings(current_user.id)
    if settings is None:
        return NotificationSettingsResponse(
            morning_motivation_enabled=False,
            inactivity_nudge_enabled=False,
            milestone_enabled=False,
            timezone="UTC",
            preferred_send_hour=8,
            inactivity_threshold_hours=72,
            last_milestone_workout_count=0,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
    return NotificationSettingsResponse.model_validate(settings)


@router.put("/settings", response_model=NotificationSettingsResponse)
async def update_notification_settings(
    payload: NotificationSettingsUpdate,
    repo: NotificationRepository = Depends(_get_repo),
    current_user: User = Depends(get_current_user),
) -> NotificationSettingsResponse:
    """Update notification settings (partial update supported)."""
    updates = payload.model_dump(exclude_none=True)
    settings = repo.upsert_settings(current_user.id, updates)
    return NotificationSettingsResponse.model_validate(settings)


@router.post("/settings/detect", response_model=NotificationSettingsResponse)
async def detect_notification_settings(
    payload: NotificationSettingsDetectRequest,
    repo: NotificationRepository = Depends(_get_repo),
    current_user: User = Depends(get_current_user),
) -> NotificationSettingsResponse:
    """Submit detected timezone/workout patterns from mobile device."""
    updates = payload.model_dump()
    settings = repo.upsert_settings(current_user.id, updates)
    return NotificationSettingsResponse.model_validate(settings)
