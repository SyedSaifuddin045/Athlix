import json

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = Field("Athelix API", alias="APP_NAME")
    app_version: str = Field("0.1.0", alias="APP_VERSION")
    app_port: int = Field(8050, alias="APP_PORT")

    debug: bool = Field(False, alias="DEBUG")

    database_host: str = Field("localhost", alias="DATABASE_HOST")
    database_port: int = Field(5432, alias="DATABASE_PORT")
    database_name: str = Field("app_db", alias="DATABASE_NAME")
    database_user: str = Field("postgres", alias="DATABASE_USER")
    database_password: str = Field("postgres", alias="DATABASE_PASSWORD")
    clerk_secret_key: str = Field(..., alias="CLERK_SECRET_KEY")
    clerk_jwks_url: str = Field(..., alias="CLERK_JWKS_URL")

    cors_allowed_origins: list[str] = Field(
        default_factory=lambda: [
            "http://localhost:3000",
            "http://localhost:8081",
            "http://localhost:5173",
            "http://127.0.0.1:3000",
            "http://127.0.0.1:5173",
            "https://athelix.fit",
            "https://www.athelix.fit",
            "capacitor://localhost",
            "ionic://localhost",
        ],
        alias="CORS_ALLOWED_ORIGINS",
    )
    cors_allow_credentials: bool = Field(True, alias="CORS_ALLOW_CREDENTIALS")
    cors_allowed_methods: list[str] = Field(
        default_factory=lambda: ["*"],
        alias="CORS_ALLOWED_METHODS",
    )
    cors_allowed_headers: list[str] = Field(
        default_factory=lambda: ["*"],
        alias="CORS_ALLOWED_HEADERS",
    )

    admin_clerk_ids: list[str] = Field(
        default_factory=list,
        alias="ADMIN_CLERK_IDS",
    )

    google_play_service_account_json: str | None = Field(None, alias="GOOGLE_PLAY_SERVICE_ACCOUNT_JSON")
    google_play_package_name: str | None = Field(None, alias="GOOGLE_PLAY_PACKAGE_NAME")
    google_group_email: str | None = Field(None, alias="GOOGLE_GROUP_EMAIL")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def database_url(self) -> str:
        # Explicitly enforce psycopg3 driver
        return (
            f"postgresql+psycopg://{self.database_user}:{self.database_password}"
            f"@{self.database_host}:{self.database_port}/{self.database_name}"
        )

    @field_validator("debug", mode="before")
    @classmethod
    def normalize_debug_value(cls, value: bool | str) -> bool | str:
        if isinstance(value, str):
            normalized = value.strip().lower()
            if normalized in {"release", "prod", "production"}:
                return False
            if normalized in {"dev", "development"}:
                return True
        return value

    @field_validator("app_port")
    @classmethod
    def validate_app_port(cls, value: int) -> int:
        if not 1 <= value <= 65535:
            raise ValueError("APP_PORT must be between 1 and 65535")
        return value

    @field_validator(
        "cors_allowed_origins",
        "cors_allowed_methods",
        "cors_allowed_headers",
        mode="before",
    )
    @classmethod
    def parse_list_setting(cls, value: list[str] | str) -> list[str] | str:
        if isinstance(value, str):
            stripped = value.strip()
            if not stripped:
                return []
            if stripped.startswith("["):
                parsed = json.loads(stripped)
                if not isinstance(parsed, list):
                    raise ValueError("Expected a JSON array")
                return [str(item).strip() for item in parsed if str(item).strip()]
            return [item.strip() for item in stripped.split(",") if item.strip()]
        return value


settings = Settings()
