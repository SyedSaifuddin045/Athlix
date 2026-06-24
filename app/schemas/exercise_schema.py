from typing import Literal
from .base_schema import BaseSchema


ExerciseCategoryLiteral = Literal["strength", "cardio", "flexibility", "other"]


class ExerciseInstructionResponse(BaseSchema):
    id: int
    step_number: int | None
    instruction: str | None


class ExerciseSecondaryMuscleResponse(BaseSchema):
    id: int
    muscle: str


class ExerciseResponse(BaseSchema):
    id: str
    name: str
    body_part: str | None
    equipment: str | None
    gif_url: str | None
    target: str | None
    exercise_category: str | None = None
    met_value: float | None = None


class ExerciseDetailResponse(ExerciseResponse):
    instructions: list[ExerciseInstructionResponse]
    secondary_muscles: list[ExerciseSecondaryMuscleResponse]


class ExerciseListResponse(BaseSchema):
    items: list[ExerciseResponse]
    total: int
    limit: int
    offset: int


class ExerciseFiltersResponse(BaseSchema):
    body_parts: list[str]
    equipment: list[str]
    targets: list[str]
    categories: list[str]
