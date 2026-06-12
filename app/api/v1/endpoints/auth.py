from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.core.clerk import verify_clerk_webhook
from app.models.user import User
from app.schemas.user_schema import UserResponse

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)) -> UserResponse:
    return UserResponse.model_validate(current_user)


@router.post("/webhook", status_code=status.HTTP_200_OK)
async def clerk_webhook(request: Request, db: Session = Depends(get_db)):
    svix_signature = request.headers.get("svix-signature") or request.headers.get("webhook-signature", "")
    if not svix_signature:
        raise HTTPException(status_code=400, detail="Missing webhook signature")

    payload = await request.body()

    try:
        event = verify_clerk_webhook(payload, svix_signature)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    event_type = event.get("type", "")
    data = event.get("data", {})

    if event_type == "user.created":
        clerk_id = data.get("id")
        email = ""
        email_addresses = data.get("email_addresses", [])
        if email_addresses:
            email = email_addresses[0].get("email_address", "")
        username = data.get("username") or email.split("@")[0]
        first_name = data.get("first_name") or ""
        last_name = data.get("last_name") or ""

        existing = db.execute(
            select(User).where(User.clerk_id == clerk_id)
        ).scalar_one_or_none()
        if existing:
            existing.email = email
            existing.username = username
            existing.first_name = first_name or None
            existing.last_name = last_name or None
            existing.updated_at = datetime.now(timezone.utc)
            db.commit()
        else:
            now = datetime.now(timezone.utc)
            user = User(
                clerk_id=clerk_id,
                username=username,
                email=email,
                first_name=first_name or None,
                last_name=last_name or None,
                created_at=now,
                updated_at=now,
            )
            db.add(user)
            db.commit()

    elif event_type == "user.updated":
        clerk_id = data.get("id")
        user = db.execute(
            select(User).where(User.clerk_id == clerk_id)
        ).scalar_one_or_none()
        if user:
            email_addresses = data.get("email_addresses", [])
            if email_addresses:
                user.email = email_addresses[0].get("email_address", user.email)
            user.username = data.get("username", user.username)
            user.first_name = data.get("first_name", user.first_name) or None
            user.last_name = data.get("last_name", user.last_name) or None
            user.updated_at = datetime.now(timezone.utc)
            db.commit()

    elif event_type == "user.deleted":
        clerk_id = data.get("id")
        user = db.execute(
            select(User).where(User.clerk_id == clerk_id)
        ).scalar_one_or_none()
        if user:
            db.delete(user)
            db.commit()

    return {"ok": True}
