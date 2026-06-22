from datetime import datetime

from sqlalchemy import TIMESTAMP, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class WaitlistEntry(Base):
    __tablename__ = "waitlist_entries"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str]
    email: Mapped[str] = mapped_column(Text)
    clerk_user_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True))

    __table_args__ = (
        UniqueConstraint("email", name="uq_waitlist_email"),
    )
