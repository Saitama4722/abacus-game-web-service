"""
Team routes: list teams, team detail, and CRUD (create, edit, delete).

Access: create/edit require admin or moderator; delete requires admin only.
"""

import logging
from pathlib import Path
from typing import Annotated, Union

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session, selectinload
from starlette.exceptions import HTTPException

from app.database import get_db
from app.deps import get_csrf_token, require_admin, require_admin_or_moderator, validate_csrf
from app.models import GameTeam, Result, Team, User

logger = logging.getLogger(__name__)


def _log_user(request: Request) -> str:
    """Return 'username (id=X)' or 'anonymous' for logging."""
    user = getattr(request.state, "user", None)
    if user is None:
        return "anonymous"
    return f"{user.username} (id={user.id}, role={user.role})"


router = APIRouter(prefix="/teams", tags=["teams"])
templates = Jinja2Templates(
    directory=str(Path(__file__).resolve().parent.parent.parent / "templates")
)


def _can_manage_teams(user: User | None) -> bool:
    """Return True if user can create/edit teams (admin or moderator)."""
    return user is not None and user.role in ("admin", "moderator")


def _can_delete_teams(user: User | None) -> bool:
    """Return True if user can delete teams (admin only)."""
    return user is not None and user.role == "admin"


@router.get("", response_class=HTMLResponse)
@router.get("/", response_class=HTMLResponse)
async def teams_list(
    request: Request,
    db: Annotated[Session, Depends(get_db)],
) -> HTMLResponse:
    """List all teams with member count. Renders teams/list.html."""
    logger.info("GET /teams - User %s", _log_user(request))
    teams = (
        db.query(Team)
        .options(selectinload(Team.members))
        .order_by(Team.created_at.desc())
        .all()
    )
    logger.debug("GET /teams - found %s teams - Status: 200", len(teams))
    user = getattr(request.state, "user", None)
    return templates.TemplateResponse(
        "teams/list.html",
        {
            "request": request,
            "teams": teams,
            "can_manage": _can_manage_teams(user),
            "can_delete": _can_delete_teams(user),
        },
    )


@router.get("/create", response_class=HTMLResponse, response_model=None)
async def team_create_form(
    request: Request,
    current_user: Annotated[Union[User, RedirectResponse], Depends(require_admin_or_moderator)],
    db: Annotated[Session, Depends(get_db)],
) -> Union[HTMLResponse, RedirectResponse]:
    """Show form to create a new team. Admin or moderator only."""
    logger.info("GET /teams/create - User %s", _log_user(request))
    if isinstance(current_user, RedirectResponse):
        return current_user
    return templates.TemplateResponse(
        "teams/create.html",
        {
            "request": request,
            "csrf_token": get_csrf_token(request),
            "team": None,
            "errors": {},
        },
    )


@router.post("/create", response_class=RedirectResponse, response_model=None)
async def team_create_submit(
    request: Request,
    current_user: Annotated[Union[User, RedirectResponse], Depends(require_admin_or_moderator)],
    db: Annotated[Session, Depends(get_db)],
    name: str = Form(""),
    csrf_token: str = Form(""),
) -> Union[RedirectResponse, HTMLResponse]:
    """Create a new team. Admin or moderator only. Validates name and CSRF."""
    logger.info("POST /teams/create - User %s - name=%r", _log_user(request), name)
    if isinstance(current_user, RedirectResponse):
        return current_user
    validate_csrf(request, csrf_token)
    name = (name or "").strip()
    errors = {}
    if not name:
        errors["name"] = "Название команды обязательно."
    if len(name) > 128:
        errors["name"] = "Название не должно превышать 128 символов."
    if errors:
        logger.warning("POST /teams/create - validation errors: %s - Status: 400", errors)
        return templates.TemplateResponse(
            "teams/create.html",
            {
                "request": request,
                "csrf_token": get_csrf_token(request),
                "team": {"name": name},
                "errors": errors,
            },
            status_code=400,
        )
    team = Team(name=name)
    db.add(team)
    db.commit()
    db.refresh(team)
    request.session.setdefault("flash", []).append(("success", "Команда успешно создана."))
    logger.info("POST /teams/create - Team created: id=%s name=%s - User %s - Result: success - Status: 303", team.id, team.name, _log_user(request))
    return RedirectResponse(url=f"/teams/{team.id}", status_code=303)


@router.get("/{team_id:int}/edit", response_class=HTMLResponse, response_model=None)
async def team_edit_form(
    request: Request,
    team_id: int,
    current_user: Annotated[Union[User, RedirectResponse], Depends(require_admin_or_moderator)],
    db: Annotated[Session, Depends(get_db)],
) -> Union[HTMLResponse, RedirectResponse]:
    """Show form to edit team. Admin or moderator only. 404 if team not found."""
    logger.info("GET /teams/%s/edit - User %s", team_id, _log_user(request))
    if isinstance(current_user, RedirectResponse):
        return current_user
    team = db.query(Team).filter(Team.id == team_id).first()
    if team is None:
        logger.warning("GET /teams/%s/edit - Team not found - Status: 404", team_id)
        raise HTTPException(status_code=404, detail="Команда не найдена")
    return templates.TemplateResponse(
        "teams/edit.html",
        {
            "request": request,
            "team": team,
            "csrf_token": get_csrf_token(request),
            "errors": {},
        },
    )


@router.post("/{team_id:int}/edit", response_class=RedirectResponse, response_model=None)
async def team_edit_submit(
    request: Request,
    team_id: int,
    current_user: Annotated[Union[User, RedirectResponse], Depends(require_admin_or_moderator)],
    db: Annotated[Session, Depends(get_db)],
    name: str = Form(""),
    csrf_token: str = Form(""),
) -> Union[RedirectResponse, HTMLResponse]:
    """Update team. Admin or moderator only. 404 if team not found."""
    logger.info("POST /teams/%s/edit - User %s - name=%r", team_id, _log_user(request), name)
    if isinstance(current_user, RedirectResponse):
        return current_user
    validate_csrf(request, csrf_token)
    team = db.query(Team).filter(Team.id == team_id).first()
    if team is None:
        logger.warning("POST /teams/%s/edit - Team not found - Status: 404", team_id)
        raise HTTPException(status_code=404, detail="Команда не найдена")
    name = (name or "").strip()
    errors = {}
    if not name:
        errors["name"] = "Название команды обязательно."
    if len(name) > 128:
        errors["name"] = "Название не должно превышать 128 символов."
    if errors:
        return templates.TemplateResponse(
            "teams/edit.html",
            {
                "request": request,
                "team": team,
                "form_name": name,
                "csrf_token": get_csrf_token(request),
                "errors": errors,
            },
            status_code=400,
        )
    team.name = name
    db.commit()
    request.session.setdefault("flash", []).append(("success", "Команда обновлена."))
    logger.info("POST /teams/%s/edit - Result: success - User %s - Status: 303", team_id, _log_user(request))
    return RedirectResponse(url=f"/teams/{team_id}", status_code=303)


@router.get("/{team_id:int}/delete", response_class=HTMLResponse, response_model=None)
async def team_delete_confirm(
    request: Request,
    team_id: int,
    current_user: Annotated[Union[User, RedirectResponse], Depends(require_admin)],
    db: Annotated[Session, Depends(get_db)],
) -> Union[HTMLResponse, RedirectResponse]:
    """Show confirmation page for team deletion. Admin only. 404 if team not found."""
    logger.info("GET /teams/%s/delete - User %s", team_id, _log_user(request))
    if isinstance(current_user, RedirectResponse):
        return current_user
    team = db.query(Team).filter(Team.id == team_id).first()
    if team is None:
        logger.warning("GET /teams/%s/delete - Team not found - Status: 404", team_id)
        raise HTTPException(status_code=404, detail="Команда не найдена")
    # Check if team has results or is linked to games
    has_results = db.query(Result).filter(Result.team_id == team_id).first() is not None
    has_games = db.query(GameTeam).filter(GameTeam.team_id == team_id).first() is not None
    if has_results or has_games:
        request.session.setdefault("flash", []).append(
            ("error", "Невозможно удалить команду: есть записи об играх или результатах. Сначала отвяжите команду от игр.")
        )
        return RedirectResponse(url=f"/teams/{team_id}", status_code=303)
    return templates.TemplateResponse(
        "teams/delete.html",
        {"request": request, "team": team, "csrf_token": get_csrf_token(request)},
    )


@router.post("/{team_id:int}/delete", response_class=RedirectResponse, response_model=None)
async def team_delete_submit(
    request: Request,
    team_id: int,
    current_user: Annotated[Union[User, RedirectResponse], Depends(require_admin)],
    db: Annotated[Session, Depends(get_db)],
    csrf_token: str = Form(""),
) -> Union[RedirectResponse, HTMLResponse]:
    """Delete team. Admin only. Blocked if team has results or game links."""
    logger.info("POST /teams/%s/delete - User %s", team_id, _log_user(request))
    if isinstance(current_user, RedirectResponse):
        return current_user
    validate_csrf(request, csrf_token)
    team = db.query(Team).filter(Team.id == team_id).first()
    if team is None:
        logger.warning("POST /teams/%s/delete - Team not found - Status: 404", team_id)
        raise HTTPException(status_code=404, detail="Команда не найдена")
    has_results = db.query(Result).filter(Result.team_id == team_id).first() is not None
    has_games = db.query(GameTeam).filter(GameTeam.team_id == team_id).first() is not None
    if has_results or has_games:
        logger.warning("POST /teams/%s/delete - Blocked: has_results=%s has_games=%s - Status: 303", team_id, has_results, has_games)
        request.session.setdefault("flash", []).append(
            ("error", "Невозможно удалить команду: есть записи об играх или результатах.")
        )
        return RedirectResponse(url=f"/teams/{team_id}", status_code=303)
    db.delete(team)
    db.commit()
    request.session.setdefault("flash", []).append(("success", "Команда удалена."))
    logger.info("POST /teams/%s/delete - Result: success - User %s - Status: 303", team_id, _log_user(request))
    return RedirectResponse(url="/teams/", status_code=303)


@router.get("/{team_id:int}", response_class=HTMLResponse)
async def team_detail(
    request: Request,
    team_id: int,
    db: Annotated[Session, Depends(get_db)],
) -> HTMLResponse:
    """Show team detail. Returns 404 if team not found."""
    logger.info("GET /teams/%s - User %s", team_id, _log_user(request))
    team = db.query(Team).filter(Team.id == team_id).first()
    if team is None:
        logger.warning("GET /teams/%s - Team not found - Status: 404", team_id)
        raise HTTPException(status_code=404, detail="Команда не найдена")
    user = getattr(request.state, "user", None)
    return templates.TemplateResponse(
        "teams/detail.html",
        {
            "request": request,
            "team": team,
            "can_manage": _can_manage_teams(user),
            "can_delete": _can_delete_teams(user),
        },
    )
