from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import decode_access_token
from app.models.user import User

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
        payload = decode_access_token(credentials.credentials)
        subject = payload.get("sub")
        token_type = payload.get("type")
    except ValueError as exc:
        raise auth_error from exc

    if token_type != "access" or not subject:
        raise auth_error

    try:
        user_id = int(subject)
    except (TypeError, ValueError) as exc:
        raise auth_error from exc

    user = db.execute(
        select(User).where(User.id == user_id)
    ).scalar_one_or_none()
    if user is None:
        raise auth_error

    return user

__all__ = ["get_db", "get_current_user", "bearer_scheme"]
