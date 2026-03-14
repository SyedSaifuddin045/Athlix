from datetime import datetime, date

from sqlalchemy import Integer, Text, Date, ForeignKey, Numeric, TIMESTAMP
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)

    username: Mapped[str] = mapped_column(Text, unique=True)
    email: Mapped[str] = mapped_column(Text, unique=True)
    password_hash: Mapped[str] = mapped_column(Text)

    created_at: Mapped[datetime]
    updated_at: Mapped[datetime]

    profile = relationship("UserProfile", back_populates="user", uselist=False)
    weight_logs = relationship("BodyWeightLog", back_populates="user")


class UserProfile(Base):
    __tablename__ = "user_profiles"
    

    id: Mapped[int] = mapped_column(primary_key=True)

    user_id: Mapped[int] = mapped_column(
        ForeignKey("app_schema.users.id", ondelete="CASCADE")
    )

    display_name: Mapped[str | None]
    date_of_birth: Mapped[date | None]
    gender: Mapped[str | None]

    height_cm: Mapped[float | None] = mapped_column(Numeric(5, 2))
    weight_kg: Mapped[float | None] = mapped_column(Numeric(5, 2))

    fitness_level: Mapped[str | None]
    preferred_unit: Mapped[str | None]

    created_at: Mapped[datetime]
    updated_at: Mapped[datetime]

    user = relationship("User", back_populates="profile")


class BodyWeightLog(Base):
    __tablename__ = "body_weight_logs"
    

    id: Mapped[int] = mapped_column(primary_key=True)

    user_id: Mapped[int] = mapped_column(
        ForeignKey("app_schema.users.id", ondelete="CASCADE")
    )

    weight_kg: Mapped[float]
    logged_at: Mapped[date]
    notes: Mapped[str | None]

    user = relationship("User", back_populates="weight_logs")