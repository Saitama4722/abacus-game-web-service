"""
Application configuration.

Loads environment variables (optionally from .env in project root) and exposes
settings for database, session, and server. All values can be overridden via
environment variables.
"""

import os
from pathlib import Path

# Project root (parent of app/)
PROJECT_ROOT: Path = Path(__file__).resolve().parent.parent

# Load .env from project root if present (optional)
_env_file = PROJECT_ROOT / ".env"
if _env_file.exists():
    try:
        from dotenv import load_dotenv
        load_dotenv(_env_file)
    except ImportError:
        pass  # python-dotenv not installed; use env vars only


def _get_database_url() -> str:
    """Return database URL from env or default SQLite path in project root."""
    url = os.getenv("DATABASE_URL", "").strip()
    if url:
        return url
    db_path = PROJECT_ROOT / "abacus_game.db"
    return f"sqlite:///{db_path}"


def _get_bool_env(name: str, default: bool = False) -> bool:
    """Read a boolean from environment (1, true, yes → True)."""
    val = os.getenv(name, "false" if not default else "true").lower()
    return val in ("1", "true", "yes")


class Settings:
    """
    Application settings. All values can be overridden via environment variables.
    """

    # Database
    @property
    def database_url(self) -> str:
        """Database URL from env or default SQLite path."""
        return _get_database_url()

    @property
    def sql_echo(self) -> bool:
        """If True, SQLAlchemy logs SQL statements (for debugging)."""
        return _get_bool_env("SQL_ECHO", default=False)

    # Session / security (for auth)
    secret_key: str = os.getenv("SECRET_KEY", "change-me-in-production-dev-only")

    # App
    debug: bool = _get_bool_env("DEBUG", default=False)
    project_name: str = os.getenv("PROJECT_NAME", "Абакус")

    # Logging: DEBUG, INFO, WARNING, ERROR (env LOG_LEVEL). Default: INFO; if DEBUG=true then DEBUG.
    @property
    def log_level(self) -> str:
        if self.debug:
            return "DEBUG"
        return os.getenv("LOG_LEVEL", "INFO").strip().upper()

    # Server (for run.py and docs)
    host: str = os.getenv("HOST", "0.0.0.0")

    @property
    def default_port(self) -> int:
        """First port to try when starting the server (e.g. 8000)."""
        try:
            return int(os.getenv("PORT", "8000"))
        except ValueError:
            return 8000


# Singleton for import elsewhere
settings = Settings()
