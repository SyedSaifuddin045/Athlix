from fastapi import APIRouter
from fastapi.params import Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
import logging

from app.core.config import settings
from app.core.database import get_db

router = APIRouter(tags=["Health"])
logger = logging.getLogger(__name__)


@router.get("/")
async def root():
    return {
        "message": "Welcome to Athelix API",
        "version": "0.1.0"
    }


@router.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "database_url": settings.database_url
    }


@router.get("/db-test")
async def db_test(db: Session = Depends(get_db)):
    """Simple connectivity test endpoint used by tests.

    Executes a lightweight statement and reports success or an error message.
    """
    try:
        # SELECT 1 works across DBs
        result = db.execute(text("SELECT 1"))
        _ = result.scalar()
        return {"status": "success", "message": "Database connection successful"}
    except Exception as exc:
        logger.exception("Database connectivity test failed")
        return {"status": "error", "message": str(exc)}


@router.get("/db-query")
async def test_db_query(db: Session = Depends(get_db)):
    """Run a small, dialect-aware query and return a human message.

    For Postgres we attempt SELECT version(); for SQLite we call
    sqlite_version() so tests using an in-memory SQLite DB succeed.
    """
    try:
        dialect = getattr(db.bind.dialect, "name", "unknown")
        if dialect == "sqlite":
            stmt = text("SELECT sqlite_version()")
        else:
            stmt = text("SELECT version()")

        result = db.execute(stmt)
        version = result.scalar()
        return {"status": "success", "message": str(version)}
    except Exception as exc:
        logger.exception("DB query failed")
        return {"status": "error", "message": str(exc)}