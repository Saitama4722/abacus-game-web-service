"""
SQLite database connection: engine, session factory, declarative base, and init.

Provides get_db dependency for FastAPI and init_db() to create tables on startup.
All ORM models must be imported (e.g. in main.py) before calling init_db() so
they are registered with Base.metadata.
"""

import logging
from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker, declarative_base

from app.config import settings

logger = logging.getLogger(__name__)

# SQLite URL: file abacus_game.db in project root (see config.py)
DATABASE_URL: str = settings.database_url

# Engine: echo=False in production; set DEBUG or SQL_ECHO for SQL logging
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},  # Required for SQLite with FastAPI
    echo=settings.sql_echo,
)

# Session factory: one session per request (used via get_db)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for all ORM models
Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    """
    Dependency that yields a DB session. Use in route handlers via Depends(get_db).
    Ensures session is closed after request.
    """
    db = SessionLocal()
    logger.debug("DB session opened")
    try:
        yield db
    except Exception as e:
        logger.debug("DB session rollback/error: %s", type(e).__name__)
        raise
    finally:
        db.close()
        logger.debug("DB session closed")


def _migrate_add_columns() -> None:
    """
    Add new columns to existing tables (Stage 7). Safe to run multiple times.
    SQLite: ALTER TABLE ... ADD COLUMN ignores if column already exists (will fail, we catch).
    """
    from sqlalchemy import text

    migrations = [
        ("games", "status", "TEXT NOT NULL DEFAULT 'in_progress'"),
        ("games", "superbonus_winners_count", "INTEGER NOT NULL DEFAULT 1"),
        ("results", "score_base", "INTEGER NOT NULL DEFAULT 0"),
        ("results", "score_horizontal_bonus", "INTEGER NOT NULL DEFAULT 0"),
        ("results", "score_vertical_bonus", "INTEGER NOT NULL DEFAULT 0"),
        ("results", "superbonus_multiplier", "REAL NOT NULL DEFAULT 1.0"),
        ("answers", "base_points_awarded", "INTEGER NOT NULL DEFAULT 0"),
    ]
    with engine.connect() as conn:
        for table, column, col_def in migrations:
            try:
                conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {column} {col_def}"))
                conn.commit()
                logger.info("Migration: added %s.%s", table, column)
            except Exception as e:
                if "duplicate column" in str(e).lower() or "already exists" in str(e).lower():
                    pass  # already migrated
                else:
                    logger.warning("Migration %s.%s: %s", table, column, e)
                conn.rollback()


def init_db() -> None:
    """
    Create all tables defined in Base.metadata. Call after importing all models
    so that they are registered with Base (e.g. in app startup).
    Runs migration to add Stage 7 columns if tables already existed.
    """
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created or already exist.")
        _migrate_add_columns()
    except Exception as e:
        logger.exception("Failed to create database tables: %s", e)
        raise
