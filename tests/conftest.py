"""
Pytest configuration and fixtures for Abacus Game web service (Stage 10).

Uses a temporary file DB so the real abacus_game.db is not modified and
all connections (lifespan, get_db) share the same database.
Sets DATABASE_URL before app is imported so the app uses the test database.
"""

import os
import sys
import tempfile

# Use a temp file DB for tests so lifespan and get_db share the same DB.
_test_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
_test_db.close()
os.environ["DATABASE_URL"] = f"sqlite:///{_test_db.name}"

# Ensure project root is on path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import pytest
from fastapi.testclient import TestClient

from app.main import app


def _ensure_tables():
    """Ensure DB tables exist (lifespan runs on first request; trigger it)."""
    with TestClient(app) as c:
        c.get("/")


@pytest.fixture(scope="session")
def _db_ready():
    """Trigger app lifespan once so tables and admin exist for all tests."""
    _ensure_tables()
    yield
    try:
        os.unlink(_test_db.name)
    except OSError:
        pass


@pytest.fixture
def client(_db_ready, request) -> TestClient:
    """Return a test client. DB tables and default admin exist from _db_ready."""
    return TestClient(app)


@pytest.fixture
def auth_headers(client: TestClient) -> dict:
    """Log in as admin/admin and return session cookies (client follows redirects)."""
    response = client.post(
        "/auth/login",
        data={"username": "admin", "password": "admin", "next": "/"},
        follow_redirects=True,
    )
    assert response.status_code == 200
    return {"Cookie": response.headers.get("set-cookie", "")}
