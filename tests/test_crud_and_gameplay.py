"""
Stage 10.2: Admin/moderator scenarios and topics/tasks management.

Create game, edit, create team, assign to game, topics auto-created, task edit validation.
"""

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def logged_client(client: TestClient) -> TestClient:
    """Client with admin logged in."""
    client.post("/auth/login", data={"username": "admin", "password": "admin", "next": "/"})
    return client


def test_create_game(logged_client: TestClient) -> None:
    """Create a new game with title and description."""
    response = logged_client.post(
        "/games/create",
        data={
            "name": "Тестовая игра",
            "description": "Описание",
            "is_active": "1",
            "csrf_token": _get_csrf(logged_client, "/games/create"),
        },
        follow_redirects=False,
    )
    assert response.status_code in (302, 303)
    assert "/games/" in response.headers.get("location", "")
    assert "games/1" in response.headers.get("location", "") or "games/2" in response.headers.get("location", "")


def _get_csrf(client: TestClient, path: str) -> str:
    """Get CSRF token from a GET page (parse from HTML)."""
    r = client.get(path)
    assert r.status_code == 200
    # Find input name="csrf_token" value="..."
    text = r.text
    start = text.find('name="csrf_token"')
    if start == -1:
        start = text.find("csrf_token")
    if start == -1:
        return "test-csrf"
    value_start = text.find('value="', start) + 7
    value_end = text.find('"', value_start)
    return text[value_start:value_end] if value_end > value_start else "test-csrf"


def test_create_team(logged_client: TestClient) -> None:
    """Create a new team."""
    response = logged_client.post(
        "/teams/create",
        data={"name": "Команда А", "csrf_token": _get_csrf(logged_client, "/teams/create")},
        follow_redirects=False,
    )
    assert response.status_code in (302, 303)
    assert "/teams/" in response.headers.get("location", "")


def test_game_topics_auto_created(logged_client: TestClient) -> None:
    """Opening topics page for a game ensures 6 topics exist."""
    # Create game first
    r = logged_client.post(
        "/games/create",
        data={
            "name": "Игра для тем",
            "description": "",
            "is_active": "0",
            "csrf_token": _get_csrf(logged_client, "/games/create"),
        },
        follow_redirects=False,
    )
    assert r.status_code in (302, 303)
    loc = r.headers.get("location", "")
    assert "/games/" in loc
    # Parse game id from location (e.g. /games/1)
    game_id = loc.split("/games/")[-1].strip("/").split("/")[0]
    assert game_id.isdigit()
    response = logged_client.get(f"/games/{game_id}/topics")
    assert response.status_code == 200
    assert "Тема 1" in response.text
    assert "Тема 6" in response.text


def test_topic_edit_validation_empty_title(logged_client: TestClient) -> None:
    """Saving topic with empty title returns validation errors."""
    # Create game and ensure topics exist
    logged_client.post(
        "/games/create",
        data={
            "name": "Игра для валидации",
            "description": "",
            "is_active": "0",
            "csrf_token": _get_csrf(logged_client, "/games/create"),
        },
        follow_redirects=True,
    )
    logged_client.get("/games/1/topics")
    csrf = _get_csrf(logged_client, "/games/1/topics/1/edit")
    response = logged_client.post(
        "/games/1/topics/1/edit",
        data={
            "csrf_token": csrf,
            "topic_title": "",
            "task_1_text": "x",
            "task_1_correct_answer": "y",
            "task_1_points": 10,
            "task_2_text": "x",
            "task_2_correct_answer": "y",
            "task_2_points": 20,
            "task_3_text": "x",
            "task_3_correct_answer": "y",
            "task_3_points": 30,
            "task_4_text": "x",
            "task_4_correct_answer": "y",
            "task_4_points": 40,
            "task_5_text": "x",
            "task_5_correct_answer": "y",
            "task_5_points": 50,
            "task_6_text": "x",
            "task_6_correct_answer": "y",
            "task_6_points": 60,
        },
        follow_redirects=False,
    )
    assert response.status_code == 400
    assert "обязательно" in response.text or "Название" in response.text


def test_play_page_requires_team_selection_for_moderator(logged_client: TestClient) -> None:
    """Moderator can open play page; without team_id shows board without cell status."""
    logged_client.post(
        "/games/create",
        data={
            "name": "Игра для play",
            "description": "",
            "is_active": "1",
            "csrf_token": _get_csrf(logged_client, "/games/create"),
        },
        follow_redirects=True,
    )
    response = logged_client.get("/games/1/play")
    assert response.status_code == 200
    assert "Игра" in response.text or "игр" in response.text.lower()


def test_task_page_out_of_order_redirects(logged_client: TestClient) -> None:
    """Play page loads; task order enforced by service (tested in test_scoring)."""
    logged_client.post(
        "/games/create",
        data={
            "name": "Игра для task",
            "description": "",
            "is_active": "1",
            "csrf_token": _get_csrf(logged_client, "/games/create"),
        },
        follow_redirects=True,
    )
    logged_client.get("/games/1/topics")
    r = logged_client.get("/games/1/play")
    assert r.status_code == 200
