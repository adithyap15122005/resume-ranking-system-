"""
Async SQLAlchemy engine, session factory, and Base for all ORM models.
Supports both SQLite (dev) and PostgreSQL (production) via DATABASE_URL.
"""
import logging

from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from backend.core.config import settings

logger = logging.getLogger(__name__)

# ── Async Engine ──────────────────────────────────────────────────────────────

connect_args = {}
if "sqlite" in settings.DATABASE_URL:
    connect_args["check_same_thread"] = False

async_engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    connect_args=connect_args,
)

AsyncSessionLocal = async_sessionmaker(
    async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


class Base(DeclarativeBase):
    pass


# ── Dependency ────────────────────────────────────────────────────────────────

async def get_db() -> AsyncSession:
    """FastAPI dependency — yields an async DB session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


# ── Init ──────────────────────────────────────────────────────────────────────

async def init_db() -> None:
    """Create all tables and apply any missing column migrations."""
    from backend.models import job, notification, organization, ranking, resume, user  # noqa: F401

    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        # Add columns that may be missing in existing DBs after schema updates
        await conn.run_sync(_apply_missing_columns)

    logger.info("HireIQ database tables initialised.")


def _apply_missing_columns(sync_conn) -> None:
    """Add any new columns that don't yet exist in the live SQLite schema."""
    from sqlalchemy import inspect, text

    inspector = inspect(sync_conn)
    migrations = {
        "ranking_results": [
            ("semantic_score",    "REAL DEFAULT 0.0"),
            ("skill_score",       "REAL DEFAULT 0.0"),
            ("experience_score",  "REAL DEFAULT 0.0"),
        ],
    }
    for table, columns in migrations.items():
        if not inspector.has_table(table):
            continue
        existing = {col["name"] for col in inspector.get_columns(table)}
        for col_name, col_def in columns:
            if col_name not in existing:
                sync_conn.execute(
                    text(f"ALTER TABLE {table} ADD COLUMN {col_name} {col_def}")
                )
                logger.info("Auto-migrated: added %s.%s", table, col_name)
