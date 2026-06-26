from datetime import date, datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select, func, text
from sqlalchemy.orm import Session, selectinload

from app.api.deps import get_current_user, get_db
from app.core.personal_records import (
    run_pr_detector_for_session,
    sync_personal_records_for_exercises,
)
from app.models.exercise import Exercise, ExerciseInstruction
from app.exercise_cache import CANONICAL_CARDIO_EXERCISES
from app.models.mesocycle import Mesocycle
from app.models.records import PersonalRecord
from app.models.user import User
from app.models.workout import ExerciseSet, WorkoutSession, WorkoutTemplate
from app.schemas.exercise_set import (
    ExerciseSetCreate,
    ExerciseSetResponse,
    ExerciseSetUpdate,
)
from app.schemas.workout_session import (
    WorkoutSessionCreate,
    WorkoutSessionDetailResponse,
    WorkoutSessionResponse,
    WorkoutSessionUpdate,
)

router = APIRouter(prefix="/workout-sessions", tags=["Workout Sessions"])


DISTANCE_FACTORS = {"running": 1.036, "walking": 0.5, "hiking": 0.6}
HEIGHT_BASELINE = 170.0
HEIGHT_FACTOR_COEFF = 0.002


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _compute_session_stats(
    db: Session, session: WorkoutSession, user_id: int | None = None, include_prs: bool = True, include_calories: bool = True
) -> dict:
    stats = {
        "duration_minutes": None,
        "exercises_count": 0,
        "total_sets": 0,
        "total_volume": 0.0,
        "prs_count": 0,
        "calories_burned": None,
    }

    if session.finished_at and session.started_at:
        finished = session.finished_at
        started = session.started_at
        if finished.tzinfo is None:
            finished = finished.replace(tzinfo=timezone.utc)
        if started.tzinfo is None:
            started = started.replace(tzinfo=timezone.utc)
        delta = finished - started
        stats["duration_minutes"] = int(delta.total_seconds() / 60)

    sets = (
        db.execute(select(ExerciseSet).where(ExerciseSet.session_id == session.id))
        .scalars()
        .all()
    )

    if sets:
        exercise_ids = set(s.exercise_id for s in sets)
        stats["exercises_count"] = len(exercise_ids)
        stats["total_sets"] = len(sets)
        stats["total_volume"] = sum((s.weight_kg or 0) * (s.reps or 0) for s in sets)

    if include_prs and session.is_completed:
        prs = (
            db.execute(
                select(func.count(PersonalRecord.id)).where(
                    PersonalRecord.session_id == session.id
                )
            ).scalar()
            or 0
        )
        stats["prs_count"] = prs

    if include_calories and sets:
        calories_burned = _compute_calories(db, sets, user_id)
        if calories_burned is not None:
            stats["calories_burned"] = calories_burned

    return stats


def _compute_age(date_of_birth: date | None) -> int | None:
    if date_of_birth is None:
        return None
    today = date.today()
    return today.year - date_of_birth.year - (
        (today.month, today.day) < (date_of_birth.month, date_of_birth.day)
    )


def _get_profile_or_defaults(db: Session, user_id: int) -> dict:
    from app.models.user import UserProfile
    profile = db.execute(
        select(
            UserProfile.weight_kg,
            UserProfile.height_cm,
            UserProfile.gender,
            UserProfile.date_of_birth,
        ).where(UserProfile.user_id == user_id)
    ).first()
    return {
        "weight_kg": float(profile.weight_kg) if profile and profile.weight_kg else 70.0,
        "height_cm": float(profile.height_cm) if profile and profile.height_cm else 170.0,
        "gender": profile.gender if profile and profile.gender else "male",
        "age": _compute_age(profile.date_of_birth) if profile and profile.date_of_birth else 30,
    }


def _compute_bmr_hourly(
    weight_kg: float, height_cm: float, age: int, gender: str
) -> float:
    if gender.lower() in ("male", "m"):
        bmr = 10 * weight_kg + 6.25 * height_cm - 5 * age + 5
    elif gender.lower() in ("female", "f"):
        bmr = 10 * weight_kg + 6.25 * height_cm - 5 * age - 161
    else:
        bmr = 10 * weight_kg + 6.25 * height_cm - 5 * age
    return bmr / 24.0


def _get_activity_calorie_type(name: str) -> str:
    lowered = name.lower()
    if any(kw in lowered for kw in ("run", "jog")):
        return "running"
    if "walk" in lowered:
        return "walking"
    if "hike" in lowered:
        return "hiking"
    return "met"


def _compute_calories(
    db: Session, sets: list[ExerciseSet], user_id: int
) -> float | None:
    p = _get_profile_or_defaults(db, user_id)
    weight_kg = p["weight_kg"]
    height_cm = p["height_cm"]
    gender = p["gender"]
    age = p["age"]
    bmr_hr = _compute_bmr_hourly(weight_kg, height_cm, age, gender)

    exercise_ids = list(set(s.exercise_id for s in sets))
    exercise_met_map: dict[str, float | None] = {}
    exercise_name_map: dict[str, str] = {}
    for eid in exercise_ids:
        row = db.execute(
            select(Exercise.met_value, Exercise.name).where(Exercise.id == eid)
        ).first()
        exercise_met_map[eid] = float(row.met_value) if row and row.met_value is not None else None
        exercise_name_map[eid] = row.name if row else ""

    total = 0.0
    has_any_valid_set = False
    for s in sets:
        met = exercise_met_map.get(s.exercise_id)
        name = exercise_name_map.get(s.exercise_id, "")
        if s.duration_sec is None or s.duration_sec == 0:
            continue

        hours = s.duration_sec / 3600.0
        cal_type = _get_activity_calorie_type(name)
        distance_km = (s.distance_m or 0) / 1000.0

        if cal_type != "met" and distance_km > 0:
            factor = DISTANCE_FACTORS.get(cal_type, 1.036)
            cal = weight_kg * distance_km * factor
            has_any_valid_set = True
        elif met is not None:
            rpe = s.rpe if s.rpe is not None else 5.0
            height_factor = 1.0 + (height_cm - HEIGHT_BASELINE) * HEIGHT_FACTOR_COEFF if height_cm else 1.0
            cal = met * (rpe / 5.0) * weight_kg * hours * height_factor
            has_any_valid_set = True
        else:
            continue

        if bmr_hr and cal < bmr_hr * hours:
            cal = bmr_hr * hours
        total += cal

    return round(total, 1) if has_any_valid_set else None


def _compute_set_calories(
    db: Session,
    exercise_id: str,
    set_rpe: float | None,
    set_duration_sec: int | None,
    distance_m: float | None,
    user_id: int,
) -> float | None:
    if set_duration_sec is None or set_duration_sec == 0:
        return None

    p = _get_profile_or_defaults(db, user_id)
    weight_kg = p["weight_kg"]
    height_cm = p["height_cm"]
    gender = p["gender"]
    age = p["age"]
    bmr_hr = _compute_bmr_hourly(weight_kg, height_cm, age, gender)

    row = db.execute(
        select(Exercise.met_value, Exercise.name).where(Exercise.id == exercise_id)
    ).first()
    if row is None:
        return None
    met_val = float(row.met_value) if row.met_value is not None else None
    name = row.name or ""

    hours = set_duration_sec / 3600.0
    cal_type = _get_activity_calorie_type(name)
    dist_km = (distance_m or 0) / 1000.0

    if cal_type != "met" and dist_km > 0:
        factor = DISTANCE_FACTORS.get(cal_type, 1.036)
        cal = weight_kg * dist_km * factor
    elif met_val is not None:
        rpe = set_rpe if set_rpe is not None else 5.0
        height_factor = 1.0 + (height_cm - HEIGHT_BASELINE) * HEIGHT_FACTOR_COEFF if height_cm else 1.0
        cal = met_val * (rpe / 5.0) * weight_kg * hours * height_factor
    else:
        return None

    if bmr_hr and cal < bmr_hr * hours:
        cal = bmr_hr * hours

    return round(cal, 1)


def _get_workout_session(
    db: Session,
    user_id: int,
    session_id: int,
    *,
    with_sets: bool = False,
) -> WorkoutSession | None:
    statement = select(WorkoutSession).where(
        WorkoutSession.id == session_id,
        WorkoutSession.user_id == user_id,
    )
    if with_sets:
        statement = statement.options(selectinload(WorkoutSession.sets))

    return db.execute(statement).scalar_one_or_none()


def _get_exercise_set(
    db: Session,
    session_id: int,
    set_id: int,
) -> ExerciseSet | None:
    return db.execute(
        select(ExerciseSet).where(
            ExerciseSet.id == set_id,
            ExerciseSet.session_id == session_id,
        )
    ).scalar_one_or_none()


def _ensure_exercise_instructions(db: Session, exercise_id: str) -> None:
    data = CANONICAL_CARDIO_EXERCISES.get(exercise_id)
    if not data:
        return
    instructions = data.get("instructions", [])
    if not instructions:
        return
    existing_count = db.execute(
        select(func.count()).select_from(ExerciseInstruction)
        .where(ExerciseInstruction.exercise_id == exercise_id)
    ).scalar()
    if existing_count and existing_count > 0:
        return
    for i, instruction in enumerate(instructions):
        db.execute(
            text("""
                INSERT INTO app_schema.exercise_instructions
                    (exercise_id, step_number, instruction)
                VALUES (:eid, :step, :instr)
            """),
            {"eid": exercise_id, "step": i + 1, "instr": instruction},
        )


def _ensure_exercise_exists(db: Session, exercise_id: str) -> None:
    exercise = db.execute(
        select(Exercise.id).where(Exercise.id == exercise_id)
    ).scalar_one_or_none()
    if exercise is not None:
        _ensure_exercise_instructions(db, exercise_id)
        return

    if exercise_id in CANONICAL_CARDIO_EXERCISES:
        data = CANONICAL_CARDIO_EXERCISES[exercise_id]
        db.execute(
            text("""
                INSERT INTO app_schema.exercises
                    (id, name, body_part, equipment, target,
                     exercise_category, met_value)
                VALUES
                    (:id, :name, :body_part, :equipment, :target,
                     :exercise_category, :met_value)
                ON CONFLICT (id) DO NOTHING
            """),
            {
                "id": exercise_id,
                "name": data["name"],
                "body_part": data["body_part"],
                "equipment": data["equipment"],
                "target": data["target"],
                "exercise_category": data["exercise_category"],
                "met_value": data["met_value"],
            },
        )
        instructions = data.get("instructions", [])
        for i, instruction in enumerate(instructions):
            db.execute(
                text("""
                    INSERT INTO app_schema.exercise_instructions
                        (exercise_id, step_number, instruction)
                    VALUES
                        (:exercise_id, :step_number, :instruction)
                """),
                {
                    "exercise_id": exercise_id,
                    "step_number": i + 1,
                    "instruction": instruction,
                },
            )
        db.flush()
        return

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Exercise not found",
    )


def _get_session_exercise_ids(db: Session, session_id: int) -> set[str]:
    return set(
        db.execute(
            select(ExerciseSet.exercise_id)
            .where(ExerciseSet.session_id == session_id)
            .distinct()
        )
        .scalars()
        .all()
    )


def _validate_template_reference(
    db: Session,
    user_id: int,
    template_id: int | None,
) -> None:
    if template_id is None:
        return

    template = db.execute(
        select(WorkoutTemplate.id).where(
            WorkoutTemplate.id == template_id,
            WorkoutTemplate.user_id == user_id,
        )
    ).scalar_one_or_none()
    if template is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workout template not found",
        )


def _validate_mesocycle_reference(
    db: Session,
    user_id: int,
    mesocycle_id: int | None,
) -> None:
    if mesocycle_id is None:
        return

    mesocycle = db.execute(
        select(Mesocycle.id).where(
            Mesocycle.id == mesocycle_id,
            Mesocycle.user_id == user_id,
        )
    ).scalar_one_or_none()
    if mesocycle is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Mesocycle not found",
        )


@router.get("", response_model=list[WorkoutSessionResponse])
async def list_workout_sessions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[WorkoutSessionResponse]:
    sessions = (
        db.execute(
            select(WorkoutSession)
            .where(WorkoutSession.user_id == current_user.id)
            .order_by(WorkoutSession.started_at.desc(), WorkoutSession.id.desc())
        )
        .scalars()
        .all()
    )

    results = []
    for session in sessions:
        session_dict = session.__dict__.copy()
        stats = _compute_session_stats(db, session, user_id=current_user.id)
        session_dict.update(stats)
        results.append(WorkoutSessionResponse.model_validate(session_dict))

    return results


@router.post(
    "",
    response_model=WorkoutSessionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_workout_session(
    payload: WorkoutSessionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> WorkoutSessionResponse:
    payload_data = payload.model_dump()
    _validate_template_reference(db, current_user.id, payload_data["template_id"])
    _validate_mesocycle_reference(db, current_user.id, payload_data["mesocycle_id"])

    started_at = payload_data.pop("started_at") or _utcnow()
    is_completed = payload_data.pop("is_completed")
    finished_at = payload_data.get("finished_at")

    session = WorkoutSession(
        user_id=current_user.id,
        started_at=started_at,
        is_completed=is_completed or finished_at is not None,
        **payload_data,
    )
    db.add(session)
    db.commit()
    db.refresh(session)

    return WorkoutSessionResponse.model_validate(session)


@router.get("/{session_id}", response_model=WorkoutSessionDetailResponse)
async def get_workout_session(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> WorkoutSessionDetailResponse:
    session = _get_workout_session(
        db,
        current_user.id,
        session_id,
        with_sets=True,
    )
    if session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workout session not found",
        )

    session_dict = session.__dict__.copy()
    stats = _compute_session_stats(db, session, user_id=current_user.id, include_calories=True)
    session_dict.update(stats)

    if session.sets:
        enriched_sets = []
        for s in session.sets:
            s_dict = s.__dict__.copy()
            cal = _compute_set_calories(db, s.exercise_id, s.rpe, s.duration_sec, s.distance_m, current_user.id)
            s_dict["calories_burned"] = cal
            from app.schemas.exercise_set import ExerciseSetResponse
            enriched_sets.append(ExerciseSetResponse.model_validate(s_dict))
        session_dict["sets"] = enriched_sets

    return WorkoutSessionDetailResponse.model_validate(session_dict)


@router.patch("/{session_id}", response_model=WorkoutSessionResponse)
async def update_workout_session(
    session_id: int,
    payload: WorkoutSessionUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> WorkoutSessionResponse:
    session = _get_workout_session(db, current_user.id, session_id)
    if session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workout session not found",
        )

    was_completed = session.is_completed
    updates = payload.model_dump(exclude_unset=True)
    if "template_id" in updates:
        _validate_template_reference(db, current_user.id, updates["template_id"])
    if "mesocycle_id" in updates:
        _validate_mesocycle_reference(db, current_user.id, updates["mesocycle_id"])
    if (
        "finished_at" in updates
        and "is_completed" not in updates
        and updates["finished_at"] is not None
    ):
        updates["is_completed"] = True

    if not updates:
        return WorkoutSessionResponse.model_validate(session)

    try:
        for field, value in updates.items():
            setattr(session, field, value)

        db.flush()
        affected_exercise_ids = _get_session_exercise_ids(db, session.id)
        if affected_exercise_ids:
            try:
                if session.is_completed:
                    run_pr_detector_for_session(
                        db,
                        user_id=current_user.id,
                        session_id=session.id,
                    )
                elif was_completed:
                    sync_personal_records_for_exercises(
                        db,
                        user_id=current_user.id,
                        exercise_ids=affected_exercise_ids,
                    )
            except Exception as pr_error:
                # PR detection should not block session updates
                import logging
                logging.getLogger(__name__).warning(
                    "PR detection failed for session %s: %s", session.id, pr_error
                )

        db.commit()
        db.refresh(session)

        session_dict = session.__dict__.copy()
        stats = _compute_session_stats(db, session, user_id=current_user.id)
        session_dict.update(stats)
        return WorkoutSessionResponse.model_validate(session_dict)
    except Exception as e:
        db.rollback()
        import logging
        logging.getLogger(__name__).error(
            "Failed to update workout session %s: %s", session_id, e, exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update session: {str(e)}",
        )


@router.delete("/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_workout_session(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Response:
    session = _get_workout_session(db, current_user.id, session_id)
    if session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workout session not found",
        )

    affected_exercise_ids = _get_session_exercise_ids(db, session.id)
    was_completed = session.is_completed

    if affected_exercise_ids and was_completed:
        try:
            sync_personal_records_for_exercises(
                db,
                user_id=current_user.id,
                exercise_ids=affected_exercise_ids,
            )
        except Exception as pr_error:
            import logging
            logging.getLogger(__name__).warning(
                "PR sync failed for session deletion: %s", pr_error
            )

    db.delete(session)
    db.commit()

    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{session_id}/sets", response_model=list[ExerciseSetResponse])
async def list_exercise_sets(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[ExerciseSetResponse]:
    session = _get_workout_session(db, current_user.id, session_id)
    if session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workout session not found",
        )

    exercise_sets = (
        db.execute(
            select(ExerciseSet)
            .where(ExerciseSet.session_id == session_id)
            .order_by(ExerciseSet.set_number.asc(), ExerciseSet.id.asc())
        )
        .scalars()
        .all()
    )

    return [ExerciseSetResponse.model_validate(item) for item in exercise_sets]


@router.post(
    "/{session_id}/sets",
    response_model=ExerciseSetResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_exercise_set(
    session_id: int,
    payload: ExerciseSetCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ExerciseSetResponse:
    session = _get_workout_session(db, current_user.id, session_id)
    if session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workout session not found",
        )

    _ensure_exercise_exists(db, payload.exercise_id)
    payload_data = payload.model_dump()
    logged_at = payload_data.pop("logged_at") or _utcnow()

    exercise_set = ExerciseSet(
        session_id=session_id,
        logged_at=logged_at,
        **payload_data,
    )
    db.add(exercise_set)
    db.flush()
    if session.is_completed:
        try:
            sync_personal_records_for_exercises(
                db,
                user_id=current_user.id,
                exercise_ids={exercise_set.exercise_id},
            )
        except Exception as pr_error:
            import logging
            logging.getLogger(__name__).warning(
                "PR sync failed for set creation: %s", pr_error
            )
    db.commit()
    db.refresh(exercise_set)

    return ExerciseSetResponse.model_validate(exercise_set)


@router.get("/{session_id}/sets/{set_id}", response_model=ExerciseSetResponse)
async def get_exercise_set(
    session_id: int,
    set_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ExerciseSetResponse:
    session = _get_workout_session(db, current_user.id, session_id)
    if session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workout session not found",
        )

    exercise_set = _get_exercise_set(db, session_id, set_id)
    if exercise_set is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Exercise set not found",
        )

    return ExerciseSetResponse.model_validate(exercise_set)


@router.patch("/{session_id}/sets/{set_id}", response_model=ExerciseSetResponse)
async def update_exercise_set(
    session_id: int,
    set_id: int,
    payload: ExerciseSetUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ExerciseSetResponse:
    session = _get_workout_session(db, current_user.id, session_id)
    if session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workout session not found",
        )

    exercise_set = _get_exercise_set(db, session_id, set_id)
    if exercise_set is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Exercise set not found",
        )

    previous_exercise_id = exercise_set.exercise_id
    updates = payload.model_dump(exclude_unset=True)
    if "exercise_id" in updates and updates["exercise_id"] is not None:
        _ensure_exercise_exists(db, updates["exercise_id"])

    if not updates:
        return ExerciseSetResponse.model_validate(exercise_set)

    for field, value in updates.items():
        setattr(exercise_set, field, value)

    db.flush()
    if session.is_completed:
        try:
            sync_personal_records_for_exercises(
                db,
                user_id=current_user.id,
                exercise_ids={previous_exercise_id, exercise_set.exercise_id},
            )
        except Exception as pr_error:
            import logging
            logging.getLogger(__name__).warning(
                "PR sync failed for set update: %s", pr_error
            )
    db.commit()
    db.refresh(exercise_set)

    return ExerciseSetResponse.model_validate(exercise_set)


@router.delete("/{session_id}/sets/{set_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_exercise_set(
    session_id: int,
    set_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Response:
    session = _get_workout_session(db, current_user.id, session_id)
    if session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workout session not found",
        )

    exercise_set = _get_exercise_set(db, session_id, set_id)
    if exercise_set is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Exercise set not found",
        )

    affected_exercise_id = exercise_set.exercise_id
    db.delete(exercise_set)
    db.flush()
    if session.is_completed:
        try:
            sync_personal_records_for_exercises(
                db,
                user_id=current_user.id,
                exercise_ids={affected_exercise_id},
            )
        except Exception as pr_error:
            import logging
            logging.getLogger(__name__).warning(
                "PR sync failed for set deletion: %s", pr_error
            )
    db.commit()

    return Response(status_code=status.HTTP_204_NO_CONTENT)
