from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.notifications.models import Device, NotificationHistory
from app.notifications.schemas import DeviceRegisterRequest


class NotificationRepository:
    def __init__(self, db: Session):
        self._db = db

    def get_device_by_token(self, user_id: int, push_token: str) -> Device | None:
        return self._db.execute(
            select(Device).where(
                Device.user_id == user_id,
                Device.push_token == push_token,
            )
        ).scalar_one_or_none()

    def get_active_devices(self, user_id: int) -> list[Device]:
        return list(
            self._db.execute(
                select(Device).where(Device.user_id == user_id)
            ).scalars().all()
        )

    def upsert_device(self, user_id: int, req: DeviceRegisterRequest) -> Device:
        now = datetime.now(timezone.utc)
        device = self.get_device_by_token(user_id, req.push_token)

        if device:
            device.platform = req.platform
            device.device_name = req.device_name or device.device_name
            device.app_version = req.app_version or device.app_version
            device.last_seen = now
            device.updated_at = now
        else:
            device = Device(
                user_id=user_id,
                platform=req.platform,
                push_token=req.push_token,
                device_name=req.device_name,
                app_version=req.app_version,
                created_at=now,
                updated_at=now,
                last_seen=now,
            )
            self._db.add(device)

        self._db.commit()
        self._db.refresh(device)
        return device

    def delete_device(self, device_id: int) -> None:
        device = self._db.get(Device, device_id)
        if device:
            self._db.delete(device)
            self._db.commit()

    def delete_device_by_token(self, user_id: int, push_token: str) -> bool:
        device = self.get_device_by_token(user_id, push_token)
        if device:
            self._db.delete(device)
            self._db.commit()
            return True
        return False

    def save_history(
        self,
        user_id: int,
        title: str | None,
        body: str | None,
        data: dict | None,
        provider: str,
        status: str,
        provider_response: str | None = None,
        error: str | None = None,
    ) -> NotificationHistory:
        now = datetime.now(timezone.utc)
        record = NotificationHistory(
            user_id=user_id,
            title=title,
            body=body,
            data=data,
            provider=provider,
            status=status,
            provider_response=provider_response,
            error=error,
            created_at=now,
            sent_at=now if status == "sent" else None,
        )
        self._db.add(record)
        self._db.commit()
        self._db.refresh(record)
        return record
