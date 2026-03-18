from sqlalchemy import String, Text, Integer, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


class Exercise(Base):
    __tablename__ = "exercises"

    id: Mapped[str] = mapped_column(String, primary_key=True)

    name: Mapped[str] = mapped_column(Text, nullable=False)
    body_part: Mapped[str | None] = mapped_column(Text)
    equipment: Mapped[str | None] = mapped_column(Text)
    gif_url: Mapped[str | None] = mapped_column(Text)
    target: Mapped[str | None] = mapped_column(Text)

    instructions = relationship(
        "ExerciseInstruction",
        back_populates="exercise",
        order_by="ExerciseInstruction.step_number",
    )
    secondary_muscles = relationship(
        "ExerciseSecondaryMuscle",
        back_populates="exercise",
        order_by="ExerciseSecondaryMuscle.muscle",
    )


class ExerciseInstruction(Base):
    __tablename__ = "exercise_instructions"

    id: Mapped[int] = mapped_column(primary_key=True)

    exercise_id: Mapped[str] = mapped_column(
        ForeignKey("app_schema.exercises.id", ondelete="CASCADE")
    )

    step_number: Mapped[int | None]
    instruction: Mapped[str | None]

    exercise = relationship("Exercise", back_populates="instructions")


class ExerciseSecondaryMuscle(Base):
    __tablename__ = "exercise_secondary_muscles"

    id: Mapped[int] = mapped_column(primary_key=True)

    exercise_id: Mapped[str] = mapped_column(
        ForeignKey("app_schema.exercises.id", ondelete="CASCADE")
    )

    muscle: Mapped[str]

    exercise = relationship("Exercise", back_populates="secondary_muscles")
