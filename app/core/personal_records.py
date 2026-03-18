from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.analytics import (
    DEFAULT_E1RM_FORMULA,
    calculate_e1rm,
    calculate_set_volume_load,
)
from app.models.records import PersonalRecord
from app.models.workout import ExerciseSet, WorkoutSession

SUPPORTED_RECORD_TYPES = (
    "estimated_1rm",
    "max_weight",
    "1rm",
    "3rm",
    "5rm",
    "8rm",
    "10rm",
    "max_volume",
    "max_reps",
)

SET_BASED_RECORD_TYPES = {
    "estimated_1rm",
    "max_weight",
    "1rm",
    "3rm",
    "5rm",
    "8rm",
    "10rm",
    "max_reps",
}


@dataclass
class RecordCandidate:
    record_type: str
    value: float
    achieved_on: date
    session_id: int | None
    set_id: int | None
    notes: str | None
    sort_key: tuple


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _achieved_at(exercise_set: ExerciseSet, session: WorkoutSession) -> datetime:
    return session.finished_at or exercise_set.logged_at or session.started_at or _utcnow()


def _store_best_candidate(
    candidates: dict[tuple[str, str], RecordCandidate],
    exercise_id: str,
    candidate: RecordCandidate,
) -> None:
    key = (exercise_id, candidate.record_type)
    current = candidates.get(key)
    if current is None or candidate.sort_key > current.sort_key:
        candidates[key] = candidate


def run_pr_detector_for_session(
    db: Session,
    *,
    user_id: int,
    session_id: int,
) -> None:
    exercise_ids = set(
        db.execute(
            select(ExerciseSet.exercise_id)
            .join(WorkoutSession, ExerciseSet.session_id == WorkoutSession.id)
            .where(
                WorkoutSession.id == session_id,
                WorkoutSession.user_id == user_id,
            )
            .distinct()
        ).scalars().all()
    )
    if exercise_ids:
        sync_personal_records_for_exercises(
            db,
            user_id=user_id,
            exercise_ids=exercise_ids,
        )


def sync_personal_records_for_exercises(
    db: Session,
    *,
    user_id: int,
    exercise_ids: set[str] | list[str] | tuple[str, ...],
) -> None:
    exercise_id_list = sorted({exercise_id for exercise_id in exercise_ids if exercise_id})
    if not exercise_id_list:
        return

    completed_rows = db.execute(
        select(ExerciseSet, WorkoutSession)
        .join(WorkoutSession, ExerciseSet.session_id == WorkoutSession.id)
        .where(
            WorkoutSession.user_id == user_id,
            WorkoutSession.is_completed.is_(True),
            ExerciseSet.exercise_id.in_(exercise_id_list),
        )
    ).all()

    best_candidates: dict[tuple[str, str], RecordCandidate] = {}
    volume_by_session: dict[tuple[str, int], dict[str, object]] = defaultdict(
        lambda: {"value": 0.0, "achieved_on": None, "notes": None}
    )

    for exercise_set, session in completed_rows:
        exercise_id = exercise_set.exercise_id
        achieved_at = _achieved_at(exercise_set, session)
        achieved_on = achieved_at.date()
        weight = float(exercise_set.weight_kg) if exercise_set.weight_kg is not None else None
        reps = exercise_set.reps

        if weight is not None and weight > 0:
            _store_best_candidate(
                best_candidates,
                exercise_id,
                RecordCandidate(
                    record_type="max_weight",
                    value=round(weight, 2),
                    achieved_on=achieved_on,
                    session_id=session.id,
                    set_id=exercise_set.id,
                    notes=exercise_set.notes,
                    sort_key=(round(weight, 2), reps or 0, achieved_at, exercise_set.id),
                ),
            )

            if reps is not None and reps > 0:
                estimated_1rm = calculate_e1rm(weight, reps, DEFAULT_E1RM_FORMULA)
                _store_best_candidate(
                    best_candidates,
                    exercise_id,
                    RecordCandidate(
                        record_type="estimated_1rm",
                        value=estimated_1rm,
                        achieved_on=achieved_on,
                        session_id=session.id,
                        set_id=exercise_set.id,
                        notes=exercise_set.notes,
                        sort_key=(estimated_1rm, round(weight, 2), reps, achieved_at, exercise_set.id),
                    ),
                )

                if reps in {1, 3, 5, 8, 10}:
                    _store_best_candidate(
                        best_candidates,
                        exercise_id,
                        RecordCandidate(
                            record_type=f"{reps}rm",
                            value=round(weight, 2),
                            achieved_on=achieved_on,
                            session_id=session.id,
                            set_id=exercise_set.id,
                            notes=exercise_set.notes,
                            sort_key=(round(weight, 2), achieved_at, exercise_set.id),
                        ),
                    )

                volume_key = (exercise_id, session.id)
                session_volume = volume_by_session[volume_key]
                session_volume["value"] = float(session_volume["value"]) + calculate_set_volume_load(weight, reps)
                session_volume["achieved_on"] = (
                    session.finished_at.date() if session.finished_at else session.started_at.date()
                )
                session_volume["notes"] = session.notes

        if reps is not None and reps > 0:
            _store_best_candidate(
                best_candidates,
                exercise_id,
                RecordCandidate(
                    record_type="max_reps",
                    value=float(reps),
                    achieved_on=achieved_on,
                    session_id=session.id,
                    set_id=exercise_set.id,
                    notes=exercise_set.notes,
                    sort_key=(reps, weight or 0.0, achieved_at, exercise_set.id),
                ),
            )

    for (exercise_id, session_id), volume_data in volume_by_session.items():
        volume = round(float(volume_data["value"]), 2)
        if volume <= 0:
            continue

        _store_best_candidate(
            best_candidates,
            exercise_id,
            RecordCandidate(
                record_type="max_volume",
                value=volume,
                achieved_on=volume_data["achieved_on"],
                session_id=session_id,
                set_id=None,
                notes=volume_data["notes"],
                sort_key=(volume, volume_data["achieved_on"], session_id),
            ),
        )

    existing_records = db.execute(
        select(PersonalRecord).where(
            PersonalRecord.user_id == user_id,
            PersonalRecord.exercise_id.in_(exercise_id_list),
        )
    ).scalars().all()
    existing_map = {
        (record.exercise_id, record.record_type): record
        for record in existing_records
    }

    expected_keys = set(best_candidates.keys())

    for key, record in existing_map.items():
        if key not in expected_keys:
            db.delete(record)

    for key, candidate in best_candidates.items():
        record = existing_map.get(key)
        if record is None:
            record = PersonalRecord(
                user_id=user_id,
                exercise_id=key[0],
                record_type=key[1],
                created_at=_utcnow(),
            )
            db.add(record)

        record.value = candidate.value
        record.achieved_on = candidate.achieved_on
        record.session_id = candidate.session_id
        record.set_id = candidate.set_id
        record.notes = candidate.notes

    pr_set_ids = {
        candidate.set_id
        for candidate in best_candidates.values()
        if candidate.record_type in SET_BASED_RECORD_TYPES and candidate.set_id is not None
    }
    affected_sets = db.execute(
        select(ExerciseSet)
        .join(WorkoutSession, ExerciseSet.session_id == WorkoutSession.id)
        .where(
            WorkoutSession.user_id == user_id,
            ExerciseSet.exercise_id.in_(exercise_id_list),
        )
    ).scalars().all()
    for exercise_set in affected_sets:
        exercise_set.is_pr = exercise_set.id in pr_set_ids
