"""Database session management for PostgreSQL."""

import os
from collections.abc import Generator
from contextlib import contextmanager
from typing import Any

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from .models import Base  # noqa

# Storage for singleton database components
_db_state: dict[str, Any] = {
    "engine": None,
    "session_factory": None,
}


def get_database_url() -> str:
    """Get the database URL from environment."""
    return os.environ.get("DATABASE_URL", "sqlite:///pfp_tracker.db")


def get_engine() -> Engine:
    """Get or create the database engine."""
    if _db_state["engine"] is None:
        database_url = get_database_url()
        _db_state["engine"] = create_engine(database_url, pool_pre_ping=True)
    return _db_state["engine"]


@contextmanager
def get_db() -> Generator[Session]:
    """Context manager for database sessions.

    Usage:
        with get_db() as db:
            db.query(Model).all()

    """
    if _db_state["session_factory"] is None:
        # Keep loaded attributes available after session close for detached return objects.
        _db_state["session_factory"] = sessionmaker(
            bind=get_engine(), expire_on_commit=False
        )
    session = _db_state["session_factory"]()
    session.expire_on_commit = False
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def run_migrations() -> None:
    """Run Alembic migrations to bring the database up to date."""
    from alembic.config import Config

    from alembic import command

    alembic_cfg = Config("alembic.ini")
    alembic_cfg.attributes["configure_logger"] = False
    alembic_cfg.set_main_option("sqlalchemy.url", get_database_url())
    command.upgrade(alembic_cfg, "head")


def reset_engine() -> None:
    """Reset the engine and session factory. Useful for testing."""
    if _db_state["engine"]:
        _db_state["engine"].dispose()
    _db_state["engine"] = None
    _db_state["session_factory"] = None
