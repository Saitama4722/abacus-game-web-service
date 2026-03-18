"""
Stage 10.1–10.2: Project startup and page loading tests.

Verifies: DB creation, default admin, all main pages load without 500,
auth redirects, static references.
"""

import pytest
from fastapi.testclient import TestClient


def test_home_page_loads(client: TestClient) -> None:
    """Home page (/) returns 200."""
    response = client.get("/")
    assert response.status_code == 200
    assert "Абакус" in response.text or "абакус" in response.text.lower()


def test_login_page_loads(client: TestClient) -> None:
    """Login page (/auth/login) returns 200."""
    response = client.get("/auth/login")
    assert response.status_code == 200
    assert "Вход" in response.text or "login" in response.text.lower()


def test_login_page_accepts_next_param(client: TestClient) -> None:
    """Login page with next param preserves it in form."""
    response = client.get("/auth/login?next=/admin/")
    assert response.status_code == 200
    assert 'name="next"' in response.text
    assert "/admin/" in response.text


def test_games_list_loads(client: TestClient) -> None:
    """Games list (/games/) returns 200 (no auth required for list)."""
    response = client.get("/games/")
    assert response.status_code == 200


def test_teams_list_loads(client: TestClient) -> None:
    """Teams list (/teams/) returns 200."""
    response = client.get("/teams/")
    assert response.status_code == 200


def test_admin_redirects_to_login_without_auth(client: TestClient) -> None:
    """Admin dashboard (/admin/) redirects to login when not authenticated."""
    response = client.get("/admin/", follow_redirects=False)
    assert response.status_code in (302, 303)
    assert "/auth/login" in response.headers.get("location", "")
    assert "next=" in response.headers.get("location", "")


def test_create_game_redirects_without_auth(client: TestClient) -> None:
    """Create game page requires auth."""
    response = client.get("/games/create", follow_redirects=False)
    assert response.status_code in (302, 303)
    assert "login" in response.headers.get("location", "").lower()


def test_create_team_redirects_without_auth(client: TestClient) -> None:
    """Create team page requires auth."""
    response = client.get("/teams/create", follow_redirects=False)
    assert response.status_code in (302, 303)
    assert "login" in response.headers.get("location", "").lower()


def test_admin_loads_after_login(client: TestClient) -> None:
    """Admin dashboard loads after login as admin."""
    client.post("/auth/login", data={"username": "admin", "password": "admin", "next": "/admin/"})
    response = client.get("/admin/")
    assert response.status_code == 200
    assert "Панель" in response.text or "управлен" in response.text.lower()


def test_create_game_loads_after_login(client: TestClient) -> None:
    """Create game form loads for authenticated admin."""
    client.post("/auth/login", data={"username": "admin", "password": "admin", "next": "/"})
    response = client.get("/games/create")
    assert response.status_code == 200
    assert "создан" in response.text.lower() or "назван" in response.text.lower()


def test_create_team_loads_after_login(client: TestClient) -> None:
    """Create team form loads for authenticated admin."""
    client.post("/auth/login", data={"username": "admin", "password": "admin", "next": "/"})
    response = client.get("/teams/create")
    assert response.status_code == 200


def test_static_css_available(client: TestClient) -> None:
    """Static CSS files are served."""
    r1 = client.get("/static/css/style.css")
    r2 = client.get("/static/css/custom.css")
    assert r1.status_code == 200
    assert r2.status_code == 200


def test_static_js_available(client: TestClient) -> None:
    """Static JS is served."""
    response = client.get("/static/js/main.js")
    assert response.status_code == 200


def test_nonexistent_game_404(client: TestClient) -> None:
    """Non-existent game returns 404."""
    response = client.get("/games/99999")
    assert response.status_code == 404


def test_nonexistent_team_404(client: TestClient) -> None:
    """Non-existent team returns 404."""
    response = client.get("/teams/99999")
    assert response.status_code == 404
