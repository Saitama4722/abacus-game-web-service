"""
Stage 10.2: Authentication tests.

Login with correct/wrong credentials, protected page redirect with next, logout.
"""

import pytest
from fastapi.testclient import TestClient


def test_login_success_redirects_to_next(client: TestClient) -> None:
    """Login with admin/admin redirects to next URL."""
    response = client.post(
        "/auth/login",
        data={"username": "admin", "password": "admin", "next": "/admin/"},
        follow_redirects=False,
    )
    assert response.status_code in (302, 303)
    assert response.headers.get("location") == "/admin/"
    # Session cookie should be set
    assert "session" in response.headers.get("set-cookie", "").lower() or "set-cookie" in response.headers


def test_login_success_then_admin_accessible(client: TestClient) -> None:
    """After login, admin page returns 200."""
    client.post("/auth/login", data={"username": "admin", "password": "admin", "next": "/"})
    response = client.get("/admin/")
    assert response.status_code == 200


def test_login_wrong_password_redirects_with_error(client: TestClient) -> None:
    """Wrong password redirects back to login with error=invalid."""
    response = client.post(
        "/auth/login",
        data={"username": "admin", "password": "wrong", "next": "/"},
        follow_redirects=False,
    )
    assert response.status_code in (302, 303)
    assert "login" in response.headers.get("location", "").lower()
    assert "invalid" in response.headers.get("location", "").lower()


def test_login_wrong_password_shows_message_on_page(client: TestClient) -> None:
    """After wrong password, login page shows error message."""
    client.post("/auth/login", data={"username": "admin", "password": "wrong", "next": "/"})
    response = client.get("/auth/login?error=invalid")
    assert response.status_code == 200
    assert "Неверное" in response.text or "пароль" in response.text.lower() or "имя" in response.text


def test_protected_page_redirect_includes_next(client: TestClient) -> None:
    """Accessing /admin/ without login redirects to login with next=/admin/."""
    response = client.get("/admin/", follow_redirects=False)
    assert response.status_code in (302, 303)
    loc = response.headers.get("location", "")
    assert "next=" in loc
    assert "admin" in loc or "%2F" in loc


def test_logout_clears_session(client: TestClient) -> None:
    """Logout redirects to home and subsequent admin access redirects to login."""
    client.post("/auth/login", data={"username": "admin", "password": "admin", "next": "/"})
    r1 = client.get("/admin/")
    assert r1.status_code == 200
    r2 = client.get("/auth/logout", follow_redirects=False)
    assert r2.status_code in (302, 303)
    assert r2.headers.get("location") == "/"
    r3 = client.get("/admin/", follow_redirects=False)
    assert r3.status_code in (302, 303)
    assert "login" in r3.headers.get("location", "").lower()
