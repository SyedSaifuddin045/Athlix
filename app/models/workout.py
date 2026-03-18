from datetime import datetime

from sqlalchemy import ForeignKey, Numeric
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


class WorkoutTemplate(Base):
    __tablename__ = "workout_templates"
    

    id: Mapped[int] = mapped_column(primary_key=True)

    user_id: Mapped[int] = mapped_column(
        ForeignKey("app_schema.users.id", ondelete="CASCADE")
    )

    name: Mapped[str]
    description: Mapped[str | None]

    is_public: Mapped[bool]

    created_at: Mapped[datetime]
    updated_at: Mapped[datetime]

    exercises = relationship("WorkoutTemplateExercise", back_populates="template")


class WorkoutTemplateExercise(Base):
    __tablename__ = "workout_template_exercises"
    

    id: Mapped[int] = mapped_column(primary_key=True)

    template_id: Mapped[int] = mapped_column(
        ForeignKey("app_schema.workout_templates.id", ondelete="CASCADE")
    )

    exercise_id: Mapped[str] = mapped_column(
        ForeignKey("app_schema.exercises.id", ondelete="CASCADE")
    )

    order_index: Mapped[int]

    target_sets: Mapped[int | None]
    target_reps: Mapped[int | None]

    target_rpe: Mapped[float | None] = mapped_column(Numeric(3, 1))
    rest_seconds: Mapped[int | None]

    notes: Mapped[str | None]

    template = relationship("WorkoutTemplate", back_populates="exercises")

class WorkoutSession(Base):
    __tablename__ = "workout_sessions"
    

    id: Mapped[int] = mapped_column(primary_key=True)

    user_id: Mapped[int] = mapped_column(
        ForeignKey("app_schema.users.id", ondelete="CASCADE")
    )

    template_id: Mapped[int | None] = mapped_column(
        ForeignKey("app_schema.workout_templates.id", ondelete="SET NULL")
    )

    mesocycle_id: Mapped[int | None] = mapped_column(
        ForeignKey("app_schema.mesocycles.id", ondelete="SET NULL")
    )

    name: Mapped[str | None]

    started_at: Mapped[datetime]
    finished_at: Mapped[datetime | None]

    perceived_exertion: Mapped[int | None]
    mood: Mapped[str | None]
    location: Mapped[str | None]

    notes: Mapped[str | None]

    is_completed: Mapped[bool]

    mesocycle = relationship("Mesocycle", back_populates="sessions")
    sets = relationship("ExerciseSet", back_populates="session")

class ExerciseSet(Base):
    __tablename__ = "exercise_sets"
    

    id: Mapped[int] = mapped_column(primary_key=True)

    session_id: Mapped[int] = mapped_column(
        ForeignKey("app_schema.workout_sessions.id", ondelete="CASCADE")
    )

    exercise_id: Mapped[str] = mapped_column(
        ForeignKey("app_schema.exercises.id", ondelete="CASCADE")
    )

    set_number: Mapped[int]
    set_type: Mapped[str]

    reps: Mapped[int | None]
    weight_kg: Mapped[float | None]

    duration_sec: Mapped[int | None]
    distance_m: Mapped[float | None]

    rpe: Mapped[float | None]

    is_pr: Mapped[bool]

    notes: Mapped[str | None]

    logged_at: Mapped[datetime]

    session = relationship("WorkoutSession", back_populates="sets")
