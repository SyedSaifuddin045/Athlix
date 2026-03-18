from .base_schema import BaseSchema


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
