from .base_schema import BaseSchema


class AppAuthConfigResponse(BaseSchema):
    token_type: str
    access_token_expires_in: int
    refresh_token_expires_in: int


class AppDocsConfigResponse(BaseSchema):
    docs_url: str | None
    redoc_url: str | None
    openapi_url: str | None


class AppFeaturesResponse(BaseSchema):
    auth: bool
    user_profiles: bool
    body_weight_tracking: bool
    exercises: bool
    workout_templates: bool
    workout_sessions: bool
    personal_records: bool
    progress_tracking: bool
    mesocycles: bool
    deload_suggestions: bool
    muscle_balance_reports: bool


class AppSupportedValuesResponse(BaseSchema):
    e1rm_formulas: list[str]
    personal_record_types: list[str]
    mesocycle_goals: list[str]


class AppConfigResponse(BaseSchema):
    app_name: str
    version: str
    environment: str
    auth: AppAuthConfigResponse
    docs: AppDocsConfigResponse
    features: AppFeaturesResponse
    supported_values: AppSupportedValuesResponse
