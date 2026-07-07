"""
SQLAlchemy engine, session factory, and Base for all ORM models.
Call init_db() once at startup to create all tables.
"""
import logging

from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from backend.config import settings

logger = logging.getLogger(__name__)


engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False},  # required for SQLite + FastAPI
    echo=settings.DEBUG,
)


# Enable WAL mode for better SQLite concurrency
@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_connection, _connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    """FastAPI dependency — yields a DB session and closes it after the request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Create all tables. Import models here so they register with Base."""
    from backend.models import job, ranking, resume  # noqa: F401

    Base.metadata.create_all(bind=engine)
    logger.info("Database tables initialised.")
