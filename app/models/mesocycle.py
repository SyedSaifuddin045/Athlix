from datetime import date, datetime
from typing import Optional, List

from sqlalchemy import Integer, Text, Date, ForeignKey, CheckConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.workout import WorkoutSession


class Mesocycle(Base):
    __tablename__ = "mesocycles"

    id: Mapped[int] = mapped_column(primary_key=True)

    user_id: Mapped[int] = mapped_column(
        ForeignKey("app_schema.users.id", ondelete="CASCADE"),
        nullable=False
    )

    name: Mapped[str] = mapped_column(Text, nullable=False)

    goal: Mapped[Optional[str]] = mapped_column(Text)

    started_on: Mapped[date] = mapped_column(Date, nullable=False)

    ended_on: Mapped[Optional[date]] = mapped_column(Date)

    weeks: Mapped[Optional[int]] = mapped_column(Integer)

    notes: Mapped[Optional[str]] = mapped_column(Text)

    created_at: Mapped[datetime] = mapped_column(nullable=False)

    # relationships
    sessions: Mapped[List["WorkoutSession"]] = relationship(
        "WorkoutSession",
        back_populates="mesocycle"
    )

    __table_args__ = (
        CheckConstraint(
            "goal IN ('strength', 'hypertrophy', 'endurance', 'weight_loss', 'maintenance')",
            name="mesocycles_goal_check"
        ),
    )