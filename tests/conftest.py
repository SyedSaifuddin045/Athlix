"""Test configuration and fixtures for the application."""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from starlette.testclient import TestClient

from app.main import app
from app.core.database import  get_db


@pytest.fixture(scope="session")
def test_db():
    """Create test database."""
    # Use SQLite for testing to avoid dependency on PostgreSQL
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    
    yield engine
    engine.dispose()


@pytest.fixture
def client(test_db):
    """Create test client with database dependency override."""
    def override_get_db():
        TestingSessionLocal = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=test_db
        )
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()
    
    app.dependency_overrides[get_db] = override_get_db
    
    with TestClient(app) as test_client:
        yield test_client
    
    app.dependency_overrides.clear()


@pytest.fixture
def db_session(test_db):
    """Create database session for tests."""
    TestingSessionLocal = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=test_db
    )
    connection = test_db.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)
    
    yield session
    
    session.close()
    transaction.rollback()
    connection.close()
