"""Legacy SQLAlchemy helpers (kept for backwards compatibility).

These functions are no-ops now that the project is moving to MongoDB, but they
remain to avoid import errors while endpoints are migrated.
"""

from contextlib import contextmanager
from typing import Generator

from app.core.config import settings


try:
    from sqlalchemy import create_engine
    from sqlalchemy.ext.declarative import declarative_base
    from sqlalchemy.orm import sessionmaker
except ImportError:  # pragma: no cover - SQLAlchemy might be absent
    create_engine = None  # type: ignore
    declarative_base = None  # type: ignore
    sessionmaker = None  # type: ignore


if settings.DATABASE_URL and create_engine and sessionmaker:
    engine = create_engine(
        settings.DATABASE_URL,
        connect_args={"check_same_thread": False}
        if "sqlite" in settings.DATABASE_URL
        else {},
    )
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base = declarative_base()
else:
    engine = None
    SessionLocal = None
    Base = declarative_base() if declarative_base else None


@contextmanager
def get_db() -> Generator:
    """Yield a SQLAlchemy session if configured, otherwise raise informative error."""

    if SessionLocal is None:
        raise RuntimeError(
            "SQLAlchemy database session not configured. "
            "The project is migrating to MongoDB; this endpoint needs to be updated."
        )
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Initialize SQL tables if SQLAlchemy is still enabled."""

    if Base is None or engine is None:
        print("SQL database initialization skipped (using MongoDB).")
        return
    Base.metadata.create_all(bind=engine)
    print("Database tables created successfully!")





