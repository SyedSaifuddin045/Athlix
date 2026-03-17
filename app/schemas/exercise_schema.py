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