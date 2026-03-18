import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

# Import config early to configure logging according to settings.debug
from app.api.v1.router import api_router
from app.core.config import settings

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

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allowed_origins,
    allow_credentials=settings.cors_allow_credentials,
    allow_methods=settings.cors_allowed_methods,
    allow_headers=settings.cors_allowed_headers,
)

app.include_router(api_router)


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

    uvicorn.run(app, host="0.0.0.0", port=8000, reload=settings.debug)


if __name__ == "__main__":
    main()
