import logging

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models.user import User
from app.notifications.repository import NotificationRepository
from app.notifications.schemas import (
    DeviceRegisterRequest,
    DeviceUnregisterRequest,
    DeviceResponse,
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
