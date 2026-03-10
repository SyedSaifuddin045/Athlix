from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):

    debug: bool = Field(False, alias="DEBUG")

    database_host: str = Field("localhost", alias="DATABASE_HOST")
    database_port: int = Field(5432, alias="DATABASE_PORT")
    database_name: str = Field("app_db", alias="DATABASE_NAME")
    database_user: str = Field("postgres", alias="DATABASE_USER")
    database_password: str = Field("postgres", alias="DATABASE_PASSWORD")

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


settings = Settings()