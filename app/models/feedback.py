from datetime import datetime

from sqlalchemy import ForeignKey, Text, UniqueConstraint, TIMESTAMP
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


class Feedback(Base):
    __tablename__ = "feedbacks"

    id: Mapped[int] = mapped_column(primary_key=True)

    user_id: Mapped[int] = mapped_column(
        ForeignKey("app_schema.users.id", ondelete="CASCADE")
    )

    type: Mapped[str]
    title: Mapped[str | None]
    description: Mapped[str] = mapped_column(Text)
    category: Mapped[str | None]
    status: Mapped[str]
    admin_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_public: Mapped[bool]
    upvotes_count: Mapped[int]

    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True))

    user = relationship("User")
    votes = relationship(
        "FeedbackVote",
        back_populates="feedback",
        cascade="all, delete-orphan",
    )
    comments = relationship(
        "FeedbackComment",
        back_populates="feedback",
        cascade="all, delete-orphan",
    )


class FeedbackVote(Base):
    __tablename__ = "feedback_votes"

    id: Mapped[int] = mapped_column(primary_key=True)

    feedback_id: Mapped[int] = mapped_column(
        ForeignKey("app_schema.feedbacks.id", ondelete="CASCADE")
    )
    user_id: Mapped[int] = mapped_column(
        ForeignKey("app_schema.users.id", ondelete="CASCADE")
    )

    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True))

    __table_args__ = (
        UniqueConstraint("feedback_id", "user_id", name="uq_feedback_vote"),
    )

    feedback = relationship("Feedback", back_populates="votes")


class FeedbackComment(Base):
    __tablename__ = "feedback_comments"

    id: Mapped[int] = mapped_column(primary_key=True)

    feedback_id: Mapped[int] = mapped_column(
        ForeignKey("app_schema.feedbacks.id", ondelete="CASCADE")
    )
    user_id: Mapped[int] = mapped_column(
        ForeignKey("app_schema.users.id", ondelete="CASCADE")
    )

    content: Mapped[str] = mapped_column(Text)

    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True))

    feedback = relationship("Feedback", back_populates="comments")
    user = relationship("User")
