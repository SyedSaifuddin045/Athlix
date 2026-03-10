"""Tests for application configuration."""

from sqlalchemy.engine import make_url
from app.core.config import settings


class TestSettings:

    def test_settings_instance_exists(self):
        assert settings is not None

    def test_database_url_configured(self):
        assert settings.database_url is not None
        assert isinstance(settings.database_url, str)

    def test_database_url_uses_psycopg3(self):
        assert settings.database_url.startswith("postgresql+psycopg://")

    def test_database_url_contains_credentials(self):
        db_url = settings.database_url
        assert "@" in db_url
        assert ":" in db_url.split("@")[0]

    def test_database_url_contains_host(self):
        db_url = settings.database_url
        assert "localhost" in db_url or "127.0.0.1" in db_url

    def test_database_url_contains_database(self):
        assert "app_db" in settings.database_url

    def test_sqlalchemy_driver(self):
        url = make_url(settings.database_url)
        assert url.drivername == "postgresql+psycopg"