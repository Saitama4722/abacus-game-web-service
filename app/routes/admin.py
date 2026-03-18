"""
Admin routes: dashboard and links to game/team management and results.

All routes require an authenticated admin or moderator (via require_admin_or_moderator).
"""

import logging
from pathlib import Path
from typing import Annotated, Union

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import require_admin_or_moderator
from app.models import Game, Team, User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["admin"])
templates = Jinja2Templates(
    directory=str(Path(__file__).resolve().parent.parent.parent / "templates")
)


@router.get("", response_class=HTMLResponse, response_model=None)
@router.get("/", response_class=HTMLResponse, response_model=None)
async def admin_dashboard(
    request: Request,
    current_user: Annotated[Union[User, RedirectResponse], Depends(require_admin_or_moderator)],
    db: Annotated[Session, Depends(get_db)],
) -> Union[HTMLResponse, RedirectResponse]:
    """
    Render admin dashboard with counts of games and teams.
    Requires admin or moderator role; otherwise redirects to login or home.
    """
    user = current_user if not isinstance(current_user, RedirectResponse) else None
    logger.info("GET /admin - User %s (id=%s role=%s)", getattr(user, "username", "redirect"), getattr(user, "id", None), getattr(user, "role", None))
    if isinstance(current_user, RedirectResponse):
        return current_user
    games_count = db.query(Game).count()
    teams_count = db.query(Team).count()
    logger.debug("GET /admin - games_count=%s teams_count=%s - Status: 200", games_count, teams_count)
    return templates.TemplateResponse(
        "admin/dashboard.html",
        {
            "request": request,
            "games_count": games_count,
            "teams_count": teams_count,
        },
    )
