from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.core.personal_records import SUPPORTED_RECORD_TYPES
from app.models.records import PersonalRecord
from app.models.user import User
from app.schemas.personal_record import PersonalRecordResponse

router = APIRouter(prefix="/personal-records", tags=["Personal Records"])


def _get_personal_record(
    db: Session,
    user_id: int,
    record_id: int,
) -> PersonalRecord | None:
    return db.execute(
        select(PersonalRecord).where(
            PersonalRecord.id == record_id,
            PersonalRecord.user_id == user_id,
        )
    ).scalar_one_or_none()


@router.get("", response_model=list[PersonalRecordResponse])
async def list_personal_records(
    exercise_id: str | None = Query(default=None),
    record_type: str | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[PersonalRecordResponse]:
    if record_type is not None and record_type not in SUPPORTED_RECORD_TYPES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Unsupported personal record type",
        )

    statement = select(PersonalRecord).where(PersonalRecord.user_id == current_user.id)
    if exercise_id is not None:
        statement = statement.where(PersonalRecord.exercise_id == exercise_id)
    if record_type is not None:
        statement = statement.where(PersonalRecord.record_type == record_type)

    records = db.execute(
        statement.order_by(
            PersonalRecord.achieved_on.desc(),
            PersonalRecord.created_at.desc(),
            PersonalRecord.id.desc(),
        )
    ).scalars().all()

    return [PersonalRecordResponse.model_validate(record) for record in records]


@router.get("/{record_id}", response_model=PersonalRecordResponse)
async def get_personal_record(
    record_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PersonalRecordResponse:
    record = _get_personal_record(db, current_user.id, record_id)
    if record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Personal record not found",
        )

    return PersonalRecordResponse.model_validate(record)
