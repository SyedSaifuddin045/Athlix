from datetime import datetime

from sqlalchemy import Integer, String, Text, TIMESTAMP, ForeignKey, JSON, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base


class Device(Base):
    __tablename__ = "devices"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("app_schema.users.id", ondelete="CASCADE"),
        index=True,
    )
    platform: Mapped[str] = mapped_column(String(16))
    push_token: Mapped[str] = mapped_column(Text)
    device_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    app_version: Mapped[str | None] = mapped_column(String(32), nullable=True)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True))
    last_seen: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), nullable=True)

    user = relationship("User")


class NotificationHistory(Base):
    __tablename__ = "notification_history"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("app_schema.users.id", ondelete="CASCADE"),
        index=True,
    )
    title: Mapped[str | None] = mapped_column(Text, nullable=True)
    body: Mapped[str | None] = mapped_column(Text, nullable=True)
    data: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    provider: Mapped[str] = mapped_column(String(16))
    status: Mapped[str] = mapped_column(String(16))
    provider_response: Mapped[str | None] = mapped_column(Text, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True))
    sent_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), nullable=True)


class UserNotificationSettings(Base):
    __tablename__ = "user_notification_settings"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("app_schema.users.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
    )
    # Toggles (opt-in, default False)
    morning_motivation_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    inactivity_nudge_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    milestone_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    # Schedule
    timezone: Mapped[str] = mapped_column(String(64), default="UTC")
    preferred_send_hour: Mapped[int] = mapped_column(default=8)  # 0-23 local time
    inactivity_threshold_hours: Mapped[int] = mapped_column(default=72)
    # Detection
    detected_timezone: Mapped[str | None] = mapped_column(String(64), nullable=True)
    typical_workout_hour: Mapped[int | None] = mapped_column(nullable=True)
    typical_workout_days: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    # Milestone tracking
    last_milestone_workout_count: Mapped[int] = mapped_column(default=0)
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True))

    user = relationship("User")
