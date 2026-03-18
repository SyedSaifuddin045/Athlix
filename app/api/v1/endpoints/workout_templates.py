from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.api.deps import get_current_user, get_db
from app.models.exercise import Exercise
from app.models.user import User
from app.models.workout import WorkoutTemplate, WorkoutTemplateExercise
from app.schemas.workout_template import (
    WorkoutTemplateCreate,
    WorkoutTemplateDetailResponse,
    WorkoutTemplateExerciseCreate,
    WorkoutTemplateExerciseResponse,
    WorkoutTemplateExerciseUpdate,
    WorkoutTemplateResponse,
    WorkoutTemplateUpdate,
)

router = APIRouter(prefix="/workout-templates", tags=["Workout Templates"])


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _get_template(
    db: Session,
    user_id: int,
    template_id: int,
    *,
    with_exercises: bool = False,
) -> WorkoutTemplate | None:
    statement = select(WorkoutTemplate).where(
        WorkoutTemplate.id == template_id,
        WorkoutTemplate.user_id == user_id,
    )
    if with_exercises:
        statement = statement.options(selectinload(WorkoutTemplate.exercises))

    return db.execute(statement).scalar_one_or_none()


def _get_template_exercise(
    db: Session,
    template_id: int,
    template_exercise_id: int,
) -> WorkoutTemplateExercise | None:
    return db.execute(
        select(WorkoutTemplateExercise).where(
            WorkoutTemplateExercise.id == template_exercise_id,
            WorkoutTemplateExercise.template_id == template_id,
        )
    ).scalar_one_or_none()


def _ensure_exercise_exists(db: Session, exercise_id: str) -> None:
    exercise = db.execute(
        select(Exercise.id).where(Exercise.id == exercise_id)
    ).scalar_one_or_none()
    if exercise is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Exercise not found",
        )


@router.get("", response_model=list[WorkoutTemplateResponse])
async def list_workout_templates(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[WorkoutTemplateResponse]:
    templates = db.execute(
        select(WorkoutTemplate)
        .where(WorkoutTemplate.user_id == current_user.id)
        .order_by(WorkoutTemplate.updated_at.desc(), WorkoutTemplate.id.desc())
    ).scalars().all()

    return [WorkoutTemplateResponse.model_validate(template) for template in templates]


@router.post(
    "",
    response_model=WorkoutTemplateResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_workout_template(
    payload: WorkoutTemplateCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> WorkoutTemplateResponse:
    now = _utcnow()
    template = WorkoutTemplate(
        user_id=current_user.id,
        created_at=now,
        updated_at=now,
        **payload.model_dump(),
    )
    db.add(template)
    db.commit()
    db.refresh(template)

    return WorkoutTemplateResponse.model_validate(template)


@router.get("/{template_id}", response_model=WorkoutTemplateDetailResponse)
async def get_workout_template(
    template_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> WorkoutTemplateDetailResponse:
    template = _get_template(
        db,
        current_user.id,
        template_id,
        with_exercises=True,
    )
    if template is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workout template not found",
        )

    return WorkoutTemplateDetailResponse.model_validate(template)


@router.patch("/{template_id}", response_model=WorkoutTemplateResponse)
async def update_workout_template(
    template_id: int,
    payload: WorkoutTemplateUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> WorkoutTemplateResponse:
    template = _get_template(db, current_user.id, template_id)
    if template is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workout template not found",
        )

    updates = payload.model_dump(exclude_unset=True)
    if not updates:
        return WorkoutTemplateResponse.model_validate(template)

    for field, value in updates.items():
        setattr(template, field, value)
    template.updated_at = _utcnow()

    db.commit()
    db.refresh(template)

    return WorkoutTemplateResponse.model_validate(template)


@router.delete("/{template_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_workout_template(
    template_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Response:
    template = _get_template(db, current_user.id, template_id)
    if template is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workout template not found",
        )

    db.delete(template)
    db.commit()

    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{template_id}/exercises", response_model=list[WorkoutTemplateExerciseResponse])
async def list_template_exercises(
    template_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[WorkoutTemplateExerciseResponse]:
    template = _get_template(db, current_user.id, template_id)
    if template is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workout template not found",
        )

    template_exercises = db.execute(
        select(WorkoutTemplateExercise)
        .where(WorkoutTemplateExercise.template_id == template_id)
        .order_by(
            WorkoutTemplateExercise.order_index.asc(),
            WorkoutTemplateExercise.id.asc(),
        )
    ).scalars().all()

    return [
        WorkoutTemplateExerciseResponse.model_validate(item)
        for item in template_exercises
    ]


@router.post(
    "/{template_id}/exercises",
    response_model=WorkoutTemplateExerciseResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_template_exercise(
    template_id: int,
    payload: WorkoutTemplateExerciseCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> WorkoutTemplateExerciseResponse:
    template = _get_template(db, current_user.id, template_id)
    if template is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workout template not found",
        )

    _ensure_exercise_exists(db, payload.exercise_id)

    template_exercise = WorkoutTemplateExercise(
        template_id=template_id,
        **payload.model_dump(),
    )
    template.updated_at = _utcnow()
    db.add(template_exercise)
    db.commit()
    db.refresh(template_exercise)

    return WorkoutTemplateExerciseResponse.model_validate(template_exercise)


@router.get(
    "/{template_id}/exercises/{template_exercise_id}",
    response_model=WorkoutTemplateExerciseResponse,
)
async def get_template_exercise(
    template_id: int,
    template_exercise_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> WorkoutTemplateExerciseResponse:
    template = _get_template(db, current_user.id, template_id)
    if template is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workout template not found",
        )

    template_exercise = _get_template_exercise(db, template_id, template_exercise_id)
    if template_exercise is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workout template exercise not found",
        )

    return WorkoutTemplateExerciseResponse.model_validate(template_exercise)


@router.patch(
    "/{template_id}/exercises/{template_exercise_id}",
    response_model=WorkoutTemplateExerciseResponse,
)
async def update_template_exercise(
    template_id: int,
    template_exercise_id: int,
    payload: WorkoutTemplateExerciseUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> WorkoutTemplateExerciseResponse:
    template = _get_template(db, current_user.id, template_id)
    if template is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workout template not found",
        )

    template_exercise = _get_template_exercise(db, template_id, template_exercise_id)
    if template_exercise is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workout template exercise not found",
        )

    updates = payload.model_dump(exclude_unset=True)
    if "exercise_id" in updates and updates["exercise_id"] is not None:
        _ensure_exercise_exists(db, updates["exercise_id"])

    if not updates:
        return WorkoutTemplateExerciseResponse.model_validate(template_exercise)

    for field, value in updates.items():
        setattr(template_exercise, field, value)
    template.updated_at = _utcnow()

    db.commit()
    db.refresh(template_exercise)

    return WorkoutTemplateExerciseResponse.model_validate(template_exercise)


@router.delete(
    "/{template_id}/exercises/{template_exercise_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_template_exercise(
    template_id: int,
    template_exercise_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Response:
    template = _get_template(db, current_user.id, template_id)
    if template is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workout template not found",
        )

    template_exercise = _get_template_exercise(db, template_id, template_exercise_id)
    if template_exercise is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workout template exercise not found",
        )

    template.updated_at = _utcnow()
    db.delete(template_exercise)
    db.commit()

    return Response(status_code=status.HTTP_204_NO_CONTENT)
