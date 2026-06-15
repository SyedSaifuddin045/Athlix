from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.api.deps import get_current_user, get_db
from app.core.config import settings
from app.models.feedback import Feedback, FeedbackComment, FeedbackVote
from app.models.user import User
from app.schemas.feedback import (
    FeedbackAdminUpdate,
    FeedbackCommentCreate,
    FeedbackCommentResponse,
    FeedbackCreate,
    FeedbackListResponse,
    FeedbackResponse,
    FeedbackStatus,
    FeedbackUpdate,
    FeedbackUserBrief,
)

router = APIRouter(prefix="/feedback", tags=["Feedback"])


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _get_feedback(db: Session, feedback_id: int) -> Feedback | None:
    return db.execute(
        select(Feedback)
        .options(selectinload(Feedback.user))
        .where(Feedback.id == feedback_id)
    ).scalar_one_or_none()


async def get_admin_user(
    current_user: User = Depends(get_current_user),
) -> User:
    if current_user.clerk_id not in settings.admin_clerk_ids:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return current_user


def _feedback_to_response(
    feedback: Feedback,
    db: Session,
    user_id: int | None = None,
) -> FeedbackResponse:
    has_upvoted = None
    if user_id is not None:
        vote = db.execute(
            select(FeedbackVote).where(
                FeedbackVote.feedback_id == feedback.id,
                FeedbackVote.user_id == user_id,
            )
        ).scalar_one_or_none()
        has_upvoted = vote is not None

    comment_count = db.execute(
        select(func.count()).select_from(FeedbackComment).where(
            FeedbackComment.feedback_id == feedback.id
        )
    ).scalar_one()

    return FeedbackResponse(
        id=feedback.id,
        type=feedback.type,
        title=feedback.title,
        description=feedback.description,
        category=feedback.category,
        status=feedback.status,
        admin_notes=feedback.admin_notes,
        is_public=feedback.is_public,
        upvotes_count=feedback.upvotes_count,
        has_upvoted=has_upvoted,
        comment_count=comment_count,
        user=FeedbackUserBrief(
            id=feedback.user.id,
            username=feedback.user.username,
            first_name=feedback.user.first_name,
            last_name=feedback.user.last_name,
        ),
        created_at=feedback.created_at,
        updated_at=feedback.updated_at,
    )


@router.get("", response_model=FeedbackListResponse)
async def list_feedback(
    type: str | None = None,
    status: str | None = None,
    category: str | None = None,
    sort: str = "newest",
    limit: int = 20,
    offset: int = 0,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> FeedbackListResponse:
    query = select(Feedback).options(selectinload(Feedback.user))

    if type is not None:
        query = query.where(Feedback.type == type)
    if status is not None:
        query = query.where(Feedback.status == status)
    if category is not None:
        query = query.where(Feedback.category == category)

    if sort == "newest":
        query = query.order_by(Feedback.created_at.desc(), Feedback.id.desc())
    elif sort == "top":
        query = query.order_by(Feedback.upvotes_count.desc(), Feedback.id.desc())

    total_query = select(func.count()).select_from(query.subquery())
    total = db.execute(total_query).scalar_one()

    items_query = query.limit(limit).offset(offset)
    items = db.execute(items_query).scalars().all()

    return FeedbackListResponse(
        items=[
            _feedback_to_response(f, db, current_user.id) for f in items
        ],
        total=total,
    )


@router.post("", response_model=FeedbackResponse, status_code=status.HTTP_201_CREATED)
async def create_feedback(
    payload: FeedbackCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> FeedbackResponse:
    now = _utcnow()
    feedback = Feedback(
        user_id=current_user.id,
        type=payload.type.value,
        title=payload.title,
        description=payload.description,
        category=payload.category,
        status=FeedbackStatus.UNDER_REVIEW.value,
        is_public=payload.type.value == "feature_request",
        upvotes_count=0,
        created_at=now,
        updated_at=now,
    )
    db.add(feedback)
    db.commit()
    db.refresh(feedback)

    feedback.user = current_user

    return _feedback_to_response(feedback, db, current_user.id)


@router.get("/{feedback_id}", response_model=FeedbackResponse)
async def get_feedback_detail(
    feedback_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> FeedbackResponse:
    feedback = _get_feedback(db, feedback_id)
    if feedback is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Feedback not found",
        )
    return _feedback_to_response(feedback, db, current_user.id)


@router.patch("/{feedback_id}", response_model=FeedbackResponse)
async def update_feedback(
    feedback_id: int,
    payload: FeedbackUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> FeedbackResponse:
    feedback = _get_feedback(db, feedback_id)
    if feedback is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Feedback not found",
        )
    if feedback.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update this feedback",
        )

    updates = payload.model_dump(exclude_unset=True)
    if "title" in updates:
        feedback.title = updates["title"]
    if "description" in updates:
        feedback.description = updates["description"]
    if "category" in updates:
        feedback.category = updates["category"]

    feedback.updated_at = _utcnow()
    db.commit()
    db.refresh(feedback)
    return _feedback_to_response(feedback, db, current_user.id)


@router.delete("/{feedback_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_feedback(
    feedback_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Response:
    feedback = _get_feedback(db, feedback_id)
    if feedback is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Feedback not found",
        )
    if feedback.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to delete this feedback",
        )

    db.delete(feedback)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{feedback_id}/upvote")
async def toggle_upvote(
    feedback_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    feedback = db.execute(
        select(Feedback).where(Feedback.id == feedback_id)
    ).scalar_one_or_none()
    if feedback is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Feedback not found",
        )

    existing_vote = db.execute(
        select(FeedbackVote).where(
            FeedbackVote.feedback_id == feedback_id,
            FeedbackVote.user_id == current_user.id,
        )
    ).scalar_one_or_none()

    if existing_vote is not None:
        db.delete(existing_vote)
        feedback.upvotes_count -= 1
        upvoted = False
    else:
        vote = FeedbackVote(
            feedback_id=feedback_id,
            user_id=current_user.id,
            created_at=_utcnow(),
        )
        db.add(vote)
        feedback.upvotes_count += 1
        upvoted = True

    db.commit()
    db.refresh(feedback)
    return {"upvoted": upvoted, "upvotes_count": feedback.upvotes_count}


@router.get(
    "/{feedback_id}/comments",
    response_model=list[FeedbackCommentResponse],
)
async def list_comments(
    feedback_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[FeedbackCommentResponse]:
    feedback = db.execute(
        select(Feedback).where(Feedback.id == feedback_id)
    ).scalar_one_or_none()
    if feedback is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Feedback not found",
        )

    comments = db.execute(
        select(FeedbackComment)
        .options(selectinload(FeedbackComment.user))
        .where(FeedbackComment.feedback_id == feedback_id)
        .order_by(FeedbackComment.created_at.asc())
    ).scalars().all()

    return [
        FeedbackCommentResponse(
            id=c.id,
            feedback_id=c.feedback_id,
            content=c.content,
            user=FeedbackUserBrief(
                id=c.user.id,
                username=c.user.username,
                first_name=c.user.first_name,
                last_name=c.user.last_name,
            ),
            created_at=c.created_at,
        )
        for c in comments
    ]


@router.post(
    "/{feedback_id}/comments",
    response_model=FeedbackCommentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_comment(
    feedback_id: int,
    payload: FeedbackCommentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> FeedbackCommentResponse:
    feedback = db.execute(
        select(Feedback).where(Feedback.id == feedback_id)
    ).scalar_one_or_none()
    if feedback is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Feedback not found",
        )

    comment = FeedbackComment(
        feedback_id=feedback_id,
        user_id=current_user.id,
        content=payload.content,
        created_at=_utcnow(),
    )
    db.add(comment)
    db.commit()
    db.refresh(comment)

    return FeedbackCommentResponse(
        id=comment.id,
        feedback_id=comment.feedback_id,
        content=comment.content,
        user=FeedbackUserBrief(
            id=current_user.id,
            username=current_user.username,
            first_name=current_user.first_name,
            last_name=current_user.last_name,
        ),
        created_at=comment.created_at,
    )


@router.patch("/{feedback_id}/admin", response_model=FeedbackResponse)
async def admin_update_feedback(
    feedback_id: int,
    payload: FeedbackAdminUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_admin_user),
) -> FeedbackResponse:
    feedback = _get_feedback(db, feedback_id)
    if feedback is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Feedback not found",
        )

    updates = payload.model_dump(exclude_unset=True)
    if "status" in updates:
        feedback.status = updates["status"].value
    if "admin_notes" in updates:
        feedback.admin_notes = updates["admin_notes"]

    feedback.updated_at = _utcnow()
    db.commit()
    db.refresh(feedback)
    return _feedback_to_response(feedback, db, current_user.id)
