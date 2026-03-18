from fastapi import APIRouter, Request

from app.core.analytics import SUPPORTED_E1RM_FORMULAS
from app.core.config import settings
from app.core.personal_records import SUPPORTED_RECORD_TYPES
from app.schemas.mesocycle import SUPPORTED_MESOCYCLE_GOALS
from app.schemas.meta import (
    AppAuthConfigResponse,
    AppConfigResponse,
    AppDocsConfigResponse,
    AppFeaturesResponse,
    AppSupportedValuesResponse,
)

router = APIRouter(prefix="/meta", tags=["Meta"])


@router.get("/app-config", response_model=AppConfigResponse)
async def get_app_config(request: Request) -> AppConfigResponse:
    return AppConfigResponse(
        app_name=settings.app_name,
        version=settings.app_version,
        environment="development" if settings.debug else "production",
        auth=AppAuthConfigResponse(
            token_type="bearer",
            access_token_expires_in=settings.access_token_expire_minutes * 60,
            refresh_token_expires_in=settings.refresh_token_expire_days * 24 * 60 * 60,
        ),
        docs=AppDocsConfigResponse(
            docs_url=request.app.docs_url,
            redoc_url=request.app.redoc_url,
            openapi_url=request.app.openapi_url,
        ),
        features=AppFeaturesResponse(
            auth=True,
            user_profiles=True,
            body_weight_tracking=True,
            exercises=True,
            workout_templates=True,
            workout_sessions=True,
            personal_records=True,
            progress_tracking=True,
            mesocycles=True,
            deload_suggestions=True,
            muscle_balance_reports=True,
        ),
        supported_values=AppSupportedValuesResponse(
            e1rm_formulas=list(SUPPORTED_E1RM_FORMULAS),
            personal_record_types=list(SUPPORTED_RECORD_TYPES),
            mesocycle_goals=list(SUPPORTED_MESOCYCLE_GOALS),
        ),
    )
