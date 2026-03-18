"""
FastAPI dependencies: authentication, authorization, and CSRF.

Provides get_current_user_optional, require_admin, require_admin_or_moderator,
and CSRF token helpers for forms.
"""

import secrets
from typing import Annotated, Union

from fastapi import Depends, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from starlette.exceptions import HTTPException

from app.database import get_db
from app.models import Game, User

# CSRF token key in session
CSRF_SESSION_KEY = "csrf_token"


def get_current_user_optional(
    request: Request,
    db: Annotated[Session, Depends(get_db)],
) -> User | None:
    """
    Return the current user if logged in (session has user_id), else None.
    Does not raise; use for optional auth in templates.
    """
    user_id = request.session.get("user_id")
    if user_id is None:
        return None
    user = db.get(User, user_id)
    return user


def _redirect_to_login(request: Request, next_path: str = "/") -> RedirectResponse:
    """Build redirect to login with next parameter (relative path only)."""
    if not next_path.startswith("/") or next_path.startswith("//"):
        next_path = "/"
    return RedirectResponse(
        url=f"/auth/login?next={next_path}",
        status_code=303,
    )


def require_admin(
    request: Request,
    db: Annotated[Session, Depends(get_db)],
) -> Union[User, RedirectResponse]:
    """
    Require an authenticated admin user. If not logged in, redirect to login.
    If logged in but not admin, redirect to home with 403.
    Use as Depends(require_admin) on admin-only routes.
    """
    user_id = request.session.get("user_id")
    if user_id is None:
        return _redirect_to_login(request, request.url.path or "/admin/")
    user = db.get(User, user_id)
    if user is None:
        request.session.clear()
        return _redirect_to_login(request, request.url.path or "/admin/")
    if user.role != "admin":
        return RedirectResponse(url="/?error=forbidden", status_code=303)
    return user


def require_admin_or_moderator(
    request: Request,
    db: Annotated[Session, Depends(get_db)],
) -> Union[User, RedirectResponse]:
    """
    Require an authenticated user with role admin or moderator.
    If not logged in, redirect to login. If logged in but neither role, redirect to home with 403.
    Use for create/edit routes that allow both admin and moderator.
    """
    user_id = request.session.get("user_id")
    if user_id is None:
        return _redirect_to_login(request, request.url.path or "/")
    user = db.get(User, user_id)
    if user is None:
        request.session.clear()
        return _redirect_to_login(request, request.url.path or "/")
    if user.role not in ("admin", "moderator"):
        return RedirectResponse(url="/?error=forbidden", status_code=303)
    return user


def require_authenticated(
    request: Request,
    db: Annotated[Session, Depends(get_db)],
) -> Union[User, RedirectResponse]:
    """
    Require any authenticated user (team, moderator, admin).
    If not logged in, redirect to login. Use for play/task routes.
    """
    user_id = request.session.get("user_id")
    if user_id is None:
        return _redirect_to_login(request, request.url.path or "/")
    user = db.get(User, user_id)
    if user is None:
        request.session.clear()
        return _redirect_to_login(request, request.url.path or "/")
    return user


def require_game_access(
    request: Request,
    db: Annotated[Session, Depends(get_db)],
) -> Union[tuple[User, Game], RedirectResponse]:
    """
    Require authenticated user who can access this game: admin, moderator, or team member
    whose team is in the game. game_id is taken from path (e.g. /games/1/play -> 1).
    Returns (user, game) or RedirectResponse/raises HTTPException.
    """
    from app.models import GameTeam

    game_id = request.path_params.get("game_id")
    if game_id is not None:
        game_id = int(game_id)
    else:
        raise HTTPException(status_code=400, detail="game_id отсутствует")

    user_id = request.session.get("user_id")
    if user_id is None:
        return _redirect_to_login(request, request.url.path or "/")
    user = db.get(User, user_id)
    if user is None:
        request.session.clear()
        return _redirect_to_login(request, request.url.path or "/")

    game = db.query(Game).filter(Game.id == game_id).first()
    if game is None:
        raise HTTPException(status_code=404, detail="Игра не найдена")

    if user.role in ("admin", "moderator"):
        return (user, game)

    if user.team_id is None:
        return RedirectResponse(url="/?error=forbidden", status_code=303)

    in_game = (
        db.query(GameTeam)
        .filter(GameTeam.game_id == game_id, GameTeam.team_id == user.team_id)
        .first()
    )
    if not in_game:
        return RedirectResponse(url="/?error=forbidden", status_code=303)

    return (user, game)


def get_csrf_token(request: Request) -> str:
    """
    Return the current session's CSRF token, creating one if missing.
    Use in templates: <input type="hidden" name="csrf_token" value="{{ csrf_token }}">
    """
    token = request.session.get(CSRF_SESSION_KEY)
    if not token:
        token = secrets.token_hex(32)
        request.session[CSRF_SESSION_KEY] = token
    return token


def validate_csrf(request: Request, form_token: str | None) -> None:
    """
    Validate that form_token matches the session CSRF token.
    Raises HTTPException 400 if invalid. Call in POST handlers before processing form.
    """
    session_token = request.session.get(CSRF_SESSION_KEY)
    if not session_token or not form_token or not secrets.compare_digest(session_token, form_token):
        raise HTTPException(status_code=400, detail="Недействительный токен формы. Обновите страницу и попробуйте снова.")
