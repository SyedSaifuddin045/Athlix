import logging

from datetime import datetime, timezone

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.clerk import verify_clerk_token
from app.core.database import get_db
from app.models.user import User

logger = logging.getLogger(__name__)

UTC = timezone.utc

bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    auth_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if credentials is None or credentials.scheme.lower() != "bearer":
        raise auth_error

    try:
        payload = verify_clerk_token(credentials.credentials)
        clerk_id = payload.get("sub")
    except Exception as exc:
        logger.warning("Clerk token verification failed: %s", exc)
        raise auth_error from exc

    if not clerk_id:
        raise auth_error

    user = db.execute(
        select(User).where(User.clerk_id == clerk_id)
    ).scalar_one_or_none()

    if user is None:
        email = payload.get("email") or f"{clerk_id}@clerk.placeholder"
        first_name = payload.get("first_name") or ""
        last_name = payload.get("last_name") or ""
        username = payload.get("username") or (
            f"{first_name}_{last_name}".lower().strip("_")
            if first_name or last_name
            else email.split("@")[0]
        )
        now = datetime.now(UTC)
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
        db.refresh(user)

    return user


__all__ = ["get_db", "get_current_user", "bearer_scheme"]
