from datetime import datetime, timezone

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
    import httpx

    async with httpx.AsyncClient() as client:
        clerk_res = await client.post(
            "https://api.clerk.com/v1/users",
            headers={
                "Authorization": f"Bearer {settings.clerk_secret_key}",
                "Content-Type": "application/json",
            },
            json={
                "email_address": [body.email],
                "first_name": body.name,
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

    # Google Play tester add (best-effort)
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

    import httpx

    credentials = json.loads(settings.google_play_service_account_json)
    package_name = settings.google_play_package_name

    # JWT for service account auth
    header = {"alg": "RS256", "typ": "JWT"}
    now = int(datetime.now(timezone.utc).timestamp())

    claim = {
        "iss": credentials["client_email"],
        "scope": "https://www.googleapis.com/auth/androidpublisher",
        "aud": credentials["token_uri"],
        "exp": now + 3600,
        "iat": now,
    }

    import jwt as pyjwt

    signed_jwt = pyjwt.encode(claim, credentials["private_key"], algorithm="RS256", headers=header)

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

        base_url = f"https://androidpublisher.googleapis.com/androidpublisher/v3/applications/{package_name}"

        edit_res = await client.post(
            f"{base_url}/edits",
            headers={"Authorization": f"Bearer {access_token}"},
            json={},
        )
        edit_res.raise_for_status()
        edit = edit_res.json()

        track_res = await client.get(
            f"{base_url}/edits/{edit['id']}/tracks/production",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        testers = {"emails": []}
        if track_res.is_success:
            track_data = track_res.json()
            testers = track_data.get("testers", {"emails": []})

        if email not in testers.get("emails", []):
            testers.setdefault("emails", []).append(email)

        await client.put(
            f"{base_url}/edits/{edit['id']}/tracks/production",
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
            },
            json={"track": "production", "testers": testers, "releases": []},
        )

        await client.post(
            f"{base_url}/edits/{edit['id']}:commit",
            headers={"Authorization": f"Bearer {access_token}"},
        )
