"""Database session management for PostgreSQL."""

import os
from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from .models import Base  # noqa

_engine = None
_SessionLocal = None


def get_database_url() -> str:
    """Get the database URL from environment."""
    return os.environ.get("DATABASE_URL", "sqlite:///pfp_tracker.db")


def get_engine():
    """Get or create the database engine."""
    global _engine
    if _engine is None:
        database_url = get_database_url()
        _engine = create_engine(database_url, pool_pre_ping=True)
    return _engine


@contextmanager
def get_db() -> Generator[Session, None, None]:
    """Context manager for database sessions.

    Usage:
        with get_db() as db:
            db.query(Model).all()

    """
    global _SessionLocal
    if _SessionLocal is None:
        # Keep loaded attributes available after session close for detached return objects.
        _SessionLocal = sessionmaker(bind=get_engine(), expire_on_commit=False)
    session = _SessionLocal()
    session.expire_on_commit = False
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def run_migrations():
    """Run Alembic migrations to bring the database up to date."""
    from alembic import command
    from alembic.config import Config

    alembic_cfg = Config("alembic.ini")
    alembic_cfg.attributes["configure_logger"] = False
    alembic_cfg.set_main_option("sqlalchemy.url", get_database_url())
    command.upgrade(alembic_cfg, "head")


def reset_engine():
    """Reset the engine and session factory. Useful for testing."""
    global _engine, _SessionLocal
    if _engine:
        _engine.dispose()
    _engine = None
    _SessionLocal = None
