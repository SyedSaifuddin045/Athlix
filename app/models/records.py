from datetime import datetime, date

from sqlalchemy import ForeignKey, Numeric
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class PersonalRecord(Base):
    __tablename__ = "personal_records"

    id: Mapped[int] = mapped_column(primary_key=True)

    user_id: Mapped[int] = mapped_column(
        ForeignKey("app_schema.users.id", ondelete="CASCADE")
    )

    exercise_id: Mapped[str] = mapped_column(
        ForeignKey("app_schema.exercises.id", ondelete="CASCADE")
    )

    record_type: Mapped[str]

    value: Mapped[float] = mapped_column(Numeric(8, 2))

    achieved_on: Mapped[date]

    session_id: Mapped[int | None]
    set_id: Mapped[int | None]

    notes: Mapped[str | None]

    created_at: Mapped[datetime]