"""
SQLAlchemy engine + session factory.

SessionLocal is used as a FastAPI dependency (get_db).
check_same_thread=False is required for SQLite with async-style
request handling in FastAPI.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from app.core.config import settings

engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False},  # SQLite only
    echo=settings.debug,
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)


def get_db() -> Session:
    """
    FastAPI dependency that yields a database session and
    guarantees it is closed after the request, even on error.
    """
    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()
