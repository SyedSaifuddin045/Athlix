"""Tests for database configuration and connectivity."""

import pytest
from sqlalchemy import text
from sqlalchemy.engine import make_url

from app.core.config import settings
from app.core.database import engine, SessionLocal, get_db


class TestDatabaseConfiguration:
    """Unit tests for database configuration."""

    def test_database_url_configured(self):
        """Database URL should exist and be a string."""
        assert settings.database_url is not None
        assert isinstance(settings.database_url, str)

    def test_database_url_uses_psycopg3(self):
        """Database URL should use psycopg3 driver."""
        url = make_url(settings.database_url)
        assert url.drivername == "postgresql+psycopg"

    def test_database_engine_created(self):
        """SQLAlchemy engine should be created."""
        assert engine is not None

    def test_engine_uses_psycopg3(self):
        """Engine should use psycopg3 driver."""
        assert engine.dialect.driver == "psycopg"

    def test_session_local_factory(self):
        """SessionLocal should create valid sessions."""
        session = SessionLocal()
        try:
            assert session is not None
        finally:
            session.close()

    def test_get_db_dependency(self):
        """get_db should yield a session."""
        generator = get_db()
        db = next(generator)

        try:
            assert db is not None
        finally:
            db.close()


class TestDatabaseConnectivity:
    """
    Integration tests for PostgreSQL connectivity.
    Requires PostgreSQL running locally.
    """

    @pytest.mark.integration
    def test_database_connection(self):
        """Database should accept connections."""
        with engine.connect() as connection:
            result = connection.execute(text("SELECT 1"))
            assert result.scalar() == 1

    @pytest.mark.integration
    def test_postgresql_version(self):
        """PostgreSQL version query should work."""
        with engine.connect() as connection:
            result = connection.execute(text("SELECT version()"))
            version = result.scalar()

            assert version is not None
            assert "PostgreSQL" in version

    @pytest.mark.integration
    def test_current_user(self):
        """Database should return current user."""
        with engine.connect() as connection:
            result = connection.execute(text("SELECT current_user"))
            user = result.scalar()

            assert user == settings.database_user

    @pytest.mark.integration
    def test_current_database(self):
        """Database should return current database."""
        with engine.connect() as connection:
            result = connection.execute(text("SELECT current_database()"))
            database = result.scalar()

            assert database == settings.database_name