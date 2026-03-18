import json

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = Field("Athelix API", alias="APP_NAME")
    app_version: str = Field("0.1.0", alias="APP_VERSION")

    debug: bool = Field(False, alias="DEBUG")

    database_host: str = Field("localhost", alias="DATABASE_HOST")
    database_port: int = Field(5432, alias="DATABASE_PORT")
    database_name: str = Field("app_db", alias="DATABASE_NAME")
    database_user: str = Field("postgres", alias="DATABASE_USER")
    database_password: str = Field("postgres", alias="DATABASE_PASSWORD")
    jwt_secret_key: str = Field(..., alias="JWT_SECRET_KEY")
    jwt_refresh_secret_key: str = Field(..., alias="JWT_REFRESH_SECRET_KEY")
    jwt_algorithm: str = Field("HS256", alias="JWT_ALGORITHM")
    access_token_expire_minutes: int = Field(30, alias="ACCESS_TOKEN_EXPIRE_MINUTES")
    refresh_token_expire_days: int = Field(7, alias="REFRESH_TOKEN_EXPIRE_DAYS")
    cors_allowed_origins: list[str] = Field(
        default_factory=lambda: [
            "http://localhost:3000",
            "http://localhost:5173",
            "http://127.0.0.1:3000",
            "http://127.0.0.1:5173",
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

    @field_validator("jwt_secret_key")
    @classmethod
    def validate_jwt_secret_key(cls, value: str) -> str:
        if len(value) < 32:
            raise ValueError("JWT_SECRET_KEY must be at least 32 characters long")
        return value

    @field_validator("jwt_refresh_secret_key")
    @classmethod
    def validate_jwt_refresh_secret_key(cls, value: str) -> str:
        if len(value) < 32:
            raise ValueError("JWT_REFRESH_SECRET_KEY must be at least 32 characters long")
        return value

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

    @field_validator("jwt_algorithm")
    @classmethod
    def validate_jwt_algorithm(cls, value: str) -> str:
        if value != "HS256":
            raise ValueError("Only HS256 is currently supported")
        return value

    @field_validator("access_token_expire_minutes")
    @classmethod
    def validate_access_token_expire_minutes(cls, value: int) -> int:
        if value <= 0:
            raise ValueError("ACCESS_TOKEN_EXPIRE_MINUTES must be greater than 0")
        return value

    @field_validator("refresh_token_expire_days")
    @classmethod
    def validate_refresh_token_expire_days(cls, value: int) -> int:
        if value <= 0:
            raise ValueError("REFRESH_TOKEN_EXPIRE_DAYS must be greater than 0")
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
