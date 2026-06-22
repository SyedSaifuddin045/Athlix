import secrets
from datetime import datetime, timezone

import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.core.config import settings
from app.models.waitlist import WaitlistEntry

router = APIRouter(prefix="/waitlist", tags=["Waitlist"])


class WaitlistResponse(BaseModel):
    success: bool
    join_url: str = ""
    play_url: str = ""


class WaitlistRequest(BaseModel):
    name: str
    email: EmailStr


@router.post("", response_model=WaitlistResponse)
async def submit_waitlist(
    body: WaitlistRequest,
    db: Session = Depends(get_db),
) -> WaitlistResponse:
    existing = db.execute(
        select(WaitlistEntry).where(WaitlistEntry.email == body.email)
    ).scalar_one_or_none()

    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This email is already on the waitlist.",
        )

    clerk_user_id: str | None = None

    async with httpx.AsyncClient() as client:
        username = body.name.lower().replace(" ", "_").replace(".", "_")
        password = secrets.token_urlsafe(16)

        clerk_res = await client.post(
            "https://api.clerk.com/v1/users",
            headers={
                "Authorization": f"Bearer {settings.clerk_secret_key}",
                "Content-Type": "application/json",
            },
            json={
                "email_address": [body.email],
                "username": username,
                "first_name": body.name,
                "password": password,
                "public_metadata": {"source": "landing-page-waitlist"},
            },
        )

        if clerk_res.is_success:
            data = clerk_res.json()
            clerk_user_id = data.get("id")
        elif clerk_res.status_code == 422:
            errors = clerk_res.json().get("errors", [])
            for err in errors:
                if err.get("code") == "duplicate_record":
                    clerk_user_id = "existing"
                    break
            if not clerk_user_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=errors[0]["message"] if errors else "Invalid data",
                )

    entry = WaitlistEntry(
        name=body.name,
        email=body.email,
        clerk_user_id=clerk_user_id,
        created_at=datetime.now(timezone.utc),
    )
    db.add(entry)
    db.commit()

    join_url = ""
    play_url = settings.play_optin_url or ""
    if settings.google_group_email:
        join_url = f"https://groups.google.com/g/{settings.google_group_email.split('@')[0]}"

    return WaitlistResponse(success=True, join_url=join_url, play_url=play_url)



