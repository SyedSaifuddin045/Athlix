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

    if settings.google_play_service_account_json and settings.google_play_package_name:
        try:
            await _add_google_play_tester(body.email)
        except Exception:
            pass

    entry = WaitlistEntry(
        name=body.name,
        email=body.email,
        clerk_user_id=clerk_user_id,
        created_at=datetime.now(timezone.utc),
    )
    db.add(entry)
    db.commit()

    return WaitlistResponse(success=True)


async def _add_google_play_tester(email: str) -> None:
    import json

    import jwt as pyjwt

    credentials = json.loads(settings.google_play_service_account_json)
    package_name = settings.google_play_package_name

    now = int(datetime.now(timezone.utc).timestamp())
    claim = {
        "iss": credentials["client_email"],
        "scope": "https://www.googleapis.com/auth/androidpublisher",
        "aud": credentials["token_uri"],
        "exp": now + 3600,
        "iat": now,
    }
    signed_jwt = pyjwt.encode(claim, credentials["private_key"], algorithm="RS256")

    async with httpx.AsyncClient() as client:
        token_res = await client.post(
            credentials["token_uri"],
            data={
                "grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
                "assertion": signed_jwt,
            },
        )
        token_data = token_res.json()
        access_token = token_data["access_token"]

        base = f"https://androidpublisher.googleapis.com/androidpublisher/v3/applications/{package_name}"

        edit_res = await client.post(
            f"{base}/edits",
            headers={"Authorization": f"Bearer {access_token}"},
            json={},
        )
        edit_res.raise_for_status()
        edit_id = edit_res.json()["id"]

        track_res = await client.get(
            f"{base}/edits/{edit_id}/tracks/internal",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        track = {"track": "internal", "releases": [], "testers": [{"emails": [email], "googleGroups": [], "googlePlayCommunities": []}]}
        if track_res.is_success:
            existing_track = track_res.json()
            existing_emails = []
            for t in existing_track.get("testers") or []:
                existing_emails.extend(t.get("emails") or [])
            if email in existing_emails:
                return
            track = existing_track
            if not track.get("testers"):
                track["testers"] = []
            track["testers"].append({"emails": [email], "googleGroups": [], "googlePlayCommunities": []})

        await client.put(
            f"{base}/edits/{edit_id}/tracks/internal",
            headers={"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"},
            json=track,
        )

        await client.post(
            f"{base}/edits/{edit_id}:commit",
            headers={"Authorization": f"Bearer {access_token}"},
        )
