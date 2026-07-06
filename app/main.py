import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.database import SessionLocal
from app.exercise_cache import ExerciseCache

import json
from app.notifications.providers import FCMProvider
from app.notifications.service import NotificationService
from app.notifications.repository import NotificationRepository as NotifRepo
from app.notifications.scheduler import create_scheduler, register_jobs

logger = logging.getLogger(__name__)


def _rate_limit_key(request: Request) -> str:
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        return f"user:{auth[7:32]}"
    forwarded = request.headers.get("X-Forwarded-For", "")
    if forwarded:
        return f"ip:{forwarded.split(',')[0].strip()}"
    client = request.client
    return f"ip:{client.host if client else 'unknown'}"


limiter = Limiter(key_func=_rate_limit_key, default_limits=["120/minute"])

OPENAPI_TAGS = [
    {"name": "Health", "description": "Operational health and connectivity endpoints."},
    {"name": "Meta", "description": "Public app configuration for web and mobile clients."},
    {"name": "Auth", "description": "Authentication and token lifecycle endpoints."},
    {"name": "Users", "description": "Current-user account, profile, overview, and bodyweight endpoints."},
    {"name": "Exercises", "description": "Exercise catalog browsing and filtering."},
    {"name": "Workout Templates", "description": "Reusable workout planning templates."},
    {"name": "Workout Sessions", "description": "Workout execution and exercise set logging."},
    {"name": "Personal Records", "description": "Read-only PR tracking derived from completed sessions."},
    {"name": "Progress", "description": "Exercise-level progress timelines and overload analytics."},
    {"name": "Analytics", "description": "User-level analytics and muscle balance reporting."},
    {"name": "Feedback", "description": "User feedback, feature requests, bug reports, and app reviews."},
    {"name": "Mesocycles", "description": "Optional training blocks and block-level analytics."},
]

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description=(
        "Backend API for workout tracking, exercise logging, personal record detection, "
        "mesocycle planning, and training analytics."
    ),
    openapi_tags=OPENAPI_TAGS,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allowed_origins,
    allow_credentials=settings.cors_allow_credentials,
    allow_methods=settings.cors_allowed_methods,
    allow_headers=settings.cors_allowed_headers,
)

app.add_middleware(SlowAPIMiddleware)

def _normalize_pem_key(raw: str) -> str:
    """Normalize PEM private key for Firebase credentials.

    Handles three env-var storage formats:
    1. Already properly formatted with actual newlines  → no-op
    2. Literal ``\\n`` (two chars) instead of real newlines  → replace
    3. Single continuous line (all newlines stripped)  → re-wrap at 64 chars
    """
    key = raw.replace("\\n", "\n").strip()
    if "\n" not in key:
        header = "-----BEGIN PRIVATE KEY-----"
        footer = "-----END PRIVATE KEY-----"
        if header in key and footer in key:
            body = key.split(header, 1)[1].split(footer, 1)[0].strip()
            lines = [body[i:i+64] for i in range(0, len(body), 64)]
            key = header + "\n" + "\n".join(lines) + "\n" + footer
    return key


# -- Notification Service Initialization --
if settings.fcm_project_id and settings.fcm_private_key:
    try:
        service_account_info = {
            "type": "service_account",
            "project_id": settings.fcm_project_id,
            "private_key": _normalize_pem_key(settings.fcm_private_key),
            "client_email": settings.fcm_client_email,
            "token_uri": "https://oauth2.googleapis.com/token",
        }
        fcm_provider = FCMProvider(service_account_info)
        notification_service = NotificationService(
            repository=NotifRepo(SessionLocal()),
            providers={"android": fcm_provider},
        )
        app.state.notification_service = notification_service
        logger.info("Notification service initialized with FCM")
    except Exception as exc:
        logger.warning("FCM not available: %s. Notifications disabled.", exc)
        app.state.notification_service = None
else:
    app.state.notification_service = None

# -- APScheduler Setup --
scheduler = create_scheduler(settings.database_url)

app.include_router(api_router)


@app.on_event("startup")
async def startup():
    # Warm exercise cache
    try:
        db = SessionLocal()
        ExerciseCache.load(db)
    except Exception:
        pass
    finally:
        db.close()

    # Start notification scheduler
    ns = getattr(app.state, "notification_service", None)
    if ns is not None:
        register_jobs(scheduler, ns)
        scheduler.start()
        logger.info("Notification scheduler started")
    else:
        logger.warning("Notification scheduler not started (no FCM)")


@app.on_event("shutdown")
async def shutdown():
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("Notification scheduler shut down")


def _format_validation_errors(errors: list[dict]) -> list[dict[str, str]]:
    formatted_errors: list[dict[str, str]] = []
    for error in errors:
        raw_location = [str(item) for item in error.get("loc", ())]
        scope = raw_location[0] if raw_location else "request"
        field_path = ".".join(raw_location[1:]) if len(raw_location) > 1 else scope
        formatted_errors.append(
            {
                "scope": scope,
                "field": field_path,
                "message": error.get("msg", "Invalid value"),
                "type": error.get("type", "validation_error"),
            }
        )
    return formatted_errors


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    detail = exc.detail
    message = detail if isinstance(detail, str) else "Request failed"
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "detail": detail,
            "message": message,
            "status_code": exc.status_code,
            "path": request.url.path,
        },
        headers=getattr(exc, "headers", None),
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content={
            "detail": exc.errors(),
            "message": "Validation error",
            "status_code": 422,
            "path": request.url.path,
            "field_errors": _format_validation_errors(exc.errors()),
        },
    )

# Tune uvicorn loggers to match our debug setting (config.py already
# configured basic logging level) so we get consistent verbosity.
if settings.debug:
    logging.getLogger("uvicorn").setLevel(logging.DEBUG)
    logging.getLogger("uvicorn.error").setLevel(logging.DEBUG)
    logging.getLogger("uvicorn.access").setLevel(logging.DEBUG)


def main():
    """Run the ASGI app using uvicorn.

    Use the app object directly here instead of the string import path so
    running the file as a script (python app/main.py) still works.
    """
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=settings.app_port, reload=settings.debug)


if __name__ == "__main__":
    main()
