from datetime import datetime, timezone, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.notifications.models import Device, NotificationHistory, UserNotificationSettings
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

    # -- Notification Settings --

    def get_settings(self, user_id: int) -> UserNotificationSettings | None:
        return self._db.execute(
            select(UserNotificationSettings).where(
                UserNotificationSettings.user_id == user_id
            )
        ).scalar_one_or_none()

    def upsert_settings(
        self,
        user_id: int,
        updates: dict,
    ) -> UserNotificationSettings:
        settings = self.get_settings(user_id)
        now = datetime.now(timezone.utc)

        if settings:
            for key, value in updates.items():
                if value is not None:
                    setattr(settings, key, value)
            settings.updated_at = now
        else:
            settings = UserNotificationSettings(
                user_id=user_id,
                **{k: v for k, v in updates.items() if v is not None},
                created_at=now,
                updated_at=now,
            )
            self._db.add(settings)

        self._db.commit()
        self._db.refresh(settings)
        return settings

    def get_settings_all_enabled(self, notif_type: str) -> list[UserNotificationSettings]:
        """Get all settings records with a specific notification type enabled.

        notif_type: 'morning_motivation', 'inactivity_nudge', or 'milestone'
        """
        column_map = {
            "morning_motivation": UserNotificationSettings.morning_motivation_enabled,
            "inactivity_nudge": UserNotificationSettings.inactivity_nudge_enabled,
            "milestone": UserNotificationSettings.milestone_enabled,
        }
        col = column_map.get(notif_type)
        if col is None:
            return []
        return list(
            self._db.execute(
                select(UserNotificationSettings).where(col == True)
            ).scalars().all()
        )

    def get_eligible_for_inactivity_nudge(
        self, threshold_hours: int
    ) -> list[tuple[int, str, str | None, int]]:
        """Return (user_id, timezone, last_workout_name, days_since) for inactive users."""
        from app.models.workout import WorkoutSession

        cutoff = datetime.utcnow() - timedelta(hours=threshold_hours)
        subq = (
            select(
                WorkoutSession.user_id,
                WorkoutSession.name,
                WorkoutSession.started_at,
            )
            .where(WorkoutSession.is_completed == True)
            .order_by(WorkoutSession.user_id, WorkoutSession.started_at.desc())
            .distinct(WorkoutSession.user_id)
            .subquery()
        )

        rows = self._db.execute(
            select(UserNotificationSettings, subq.c.name, subq.c.started_at)
            .outerjoin(
                subq,
                UserNotificationSettings.user_id == subq.c.user_id,
            )
            .where(
                UserNotificationSettings.inactivity_nudge_enabled == True,
                (
                    (subq.c.started_at == None)
                    | (subq.c.started_at < cutoff)
                ),
            )
        ).all()

        results = []
        for r in rows:
            last_name = r[1]
            last_date = r[2]
            days_since = (
                (datetime.utcnow() - last_date).days
                if last_date
                else 999
            )
            results.append((r[0].user_id, r[0].timezone, last_name, days_since))

        return results

    def get_eligible_for_milestone(self) -> list[tuple[int, str, int]]:
        """Return (user_id, timezone, workout_count) for users hitting new milestones."""
        from sqlalchemy import func as f
        from app.models.workout import WorkoutSession

        workout_counts = (
            select(
                WorkoutSession.user_id,
                f.count(WorkoutSession.id).label("cnt"),
            )
            .where(WorkoutSession.is_completed == True)
            .group_by(WorkoutSession.user_id)
            .subquery()
        )

        MILESTONES = [10, 25, 50, 100, 250, 500, 1000]

        rows = self._db.execute(
            select(UserNotificationSettings, workout_counts.c.cnt)
            .join(
                workout_counts,
                UserNotificationSettings.user_id == workout_counts.c.user_id,
            )
            .where(
                UserNotificationSettings.milestone_enabled == True,
            )
        ).all()

        results = []
        for r in rows:
            count = r[1]
            last_sent = r[0].last_milestone_workout_count
            for m in MILESTONES:
                if count >= m > last_sent:
                    results.append((r[0].user_id, r[0].timezone, count))
                    break

        return results

    def update_milestone_sent(self, user_id: int, count: int) -> None:
        settings = self.get_settings(user_id)
        if settings:
            settings.last_milestone_workout_count = count
            settings.updated_at = datetime.now(timezone.utc)
            self._db.commit()
