"""
Game routes: list games, game detail, and CRUD (create, edit, delete).

Access: create/edit require admin or moderator; delete requires admin only.
"""

import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Annotated, Union

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session, selectinload
from starlette.exceptions import HTTPException

from app.database import get_db
from app.deps import (
    get_csrf_token,
    require_admin,
    require_admin_or_moderator,
    require_game_access,
    require_authenticated,
    validate_csrf,
)
from app.models import Game, GameTeam, Result, Task, Team, Topic, User, Answer
from app.services.game_service import (
    check_task_available,
    finish_game as svc_finish_game,
    get_game_board_state,
    get_game_end_time,
    is_game_paused,
    is_game_time_expired,
    submit_answer as svc_submit_answer,
    _recalculate_bonuses,
)
from app.services.game_service_5x5 import (
    check_task_available_5x5,
    get_game_board_state_5x5,
    submit_answer_5x5,
    _recalculate_bonuses_5x5,
)

logger = logging.getLogger(__name__)


def _log_user(request: Request) -> str:
    user = getattr(request.state, "user", None)
    if user is None:
        return "anonymous"
    return f"{user.username} (id={user.id}, role={user.role})"

def get_num_topics(game: Game | None) -> int:
    if game and getattr(game, "game_type", "abacus") == "five_by_five":
        return 5
    return 6

def get_num_tasks(game: Game | None) -> int:
    if game and getattr(game, "game_type", "abacus") == "five_by_five":
        return 5
    return 6

DEFAULT_POINTS = [10, 20, 30, 40, 50, 60]


from app.models import Game, GameTeam, GameTopic, GameTask, Result, Task, Team, Topic, User

def _get_game_topics(game: Game) -> list["GameTopic | None"]:
    """Return slots for game topics, some may be None if not selected."""
    n_topics = get_num_topics(game)
    slots = [None] * n_topics
    for gt in game.game_topics:
        if 1 <= gt.order_index <= n_topics:
            slots[gt.order_index - 1] = gt
    return slots

def _get_game_tasks(game: Game, game_topic: "GameTopic | None") -> list["GameTask | None"]:
    """Return slots for game tasks, some may be None if not selected."""
    n_tasks = get_num_tasks(game)
    slots = [None] * n_tasks
    if game_topic:
        for gt in game_topic.game_tasks:
            if 1 <= gt.order_index <= n_tasks:
                slots[gt.order_index - 1] = gt
    return slots

router = APIRouter(prefix="/games", tags=["games"])
templates = Jinja2Templates(
    directory=str(Path(__file__).resolve().parent.parent.parent / "templates")
)


def _can_manage_games(user: User | None) -> bool:
    """Return True if user can create/edit games (admin or moderator)."""
    return user is not None and user.role in ("administrator", "moderator")


def _can_delete_games(user: User | None) -> bool:
    """Return True if user can delete games (admin only)."""
    return user is not None and user.role == "administrator"


@router.get("", response_class=HTMLResponse)
@router.get("/", response_class=HTMLResponse)
async def games_list(
    request: Request,
    db: Annotated[Session, Depends(get_db)],
) -> HTMLResponse:
    """List games: all for admin/moderator, only active for others."""
    logger.info("GET /games - User %s - Listing games", _log_user(request))
    user = getattr(request.state, "user", None)
    query = db.query(Game).order_by(Game.created_at.desc())
    if not _can_manage_games(user):
        query = query.filter(Game.is_active)
    games = query.all()
    logger.debug("GET /games - found %s games - Status: 200", len(games))
    return templates.TemplateResponse(
        "games/list.html",
        {
            "request": request,
            "games": games,
            "can_manage": _can_manage_games(user),
            "can_delete": _can_delete_games(user),
            "csrf_token": get_csrf_token(request),
        },
    )


@router.get("/{game_id:int}", response_class=HTMLResponse, response_model=None)
async def game_detail(
    request: Request,
    game_id: int,
    db: Annotated[Session, Depends(get_db)],
):
    """Show game detail with topics and teams. Returns 404 if game not found."""
    logger.info("GET /games/%s - User %s", game_id, _log_user(request))
    game = (
        db.query(Game)
        .options(selectinload(Game.game_topics).selectinload(GameTopic.game_tasks))
        .options(selectinload(Game.teams))
        .filter(Game.id == game_id)
        .first()
    )
    if game is None:
        logger.warning("GET /games/%s - Game not found - Status: 404", game_id)
        raise HTTPException(status_code=404, detail="Игра не найдена")
    
    topics_slots = _get_game_topics(game)
    user = getattr(request.state, "user", None)
    
    game_has_not_started = getattr(game, "start_time", None) is not None and datetime.utcnow() < game.start_time
    
    return templates.TemplateResponse(
        "games/detail.html",
        {
            "request": request,
            "game": game,
            "topics_slots": topics_slots,
            "can_manage": _can_manage_games(user),
            "can_delete": _can_delete_games(user),
            "csrf_token": get_csrf_token(request),
            "game_has_not_started": game_has_not_started,
        },
    )


@router.get("/create", response_class=HTMLResponse, response_model=None)
async def game_create_form(
    request: Request,
    current_user: Annotated[Union[User, RedirectResponse], Depends(require_admin_or_moderator)],
    db: Annotated[Session, Depends(get_db)],
):
    """Show form to create a new game. Admin or moderator only."""
    logger.info("GET /games/create - User %s - Show create form", _log_user(request))
    if isinstance(current_user, RedirectResponse):
        return current_user
    return templates.TemplateResponse(
        "games/create.html",
        {
            "request": request,
            "csrf_token": get_csrf_token(request),
            "game": None,
            "game_type": "abacus",
            "errors": {},
        },
    )


@router.post("/create", response_class=RedirectResponse, response_model=None)
async def game_create_submit(
    request: Request,
    current_user: Annotated[Union[User, RedirectResponse], Depends(require_admin_or_moderator)],
    db: Annotated[Session, Depends(get_db)],
    name: str = Form(""),
    description: str = Form(""),
    is_active: str = Form("0"),
    start_time: str = Form(""),
    duration_minutes: str = Form("60"),
    game_type: str = Form("abacus"),
    csrf_token: str = Form(""),
):
    """Create a new game. Admin or moderator only."""
    logger.info("POST /games/create - User %s - name=%r is_active=%s type=%s", _log_user(request), name, is_active, game_type)
    if isinstance(current_user, RedirectResponse):
        return current_user
    validate_csrf(request, csrf_token)
    name = (name or "").strip()
    description = (description or "").strip() or None
    if game_type not in ("abacus", "five_by_five"):
        game_type = "abacus"
        
    errors = {}
    if not name:
        errors["name"] = "Название игры обязательно."
    if len(name) > 128:
        errors["name"] = "Название не должно превышать 128 символов."
    if errors:
        return templates.TemplateResponse(
            "games/create.html",
            {
                "request": request,
                "csrf_token": get_csrf_token(request),
                "game": {"name": name, "description": description or ""},
                "is_active": is_active,
                "game_type": game_type,
                "errors": errors,
            },
            status_code=400,
        )
    # Parse time fields
    parsed_start = None
    if (start_time or "").strip():
        try:
            parsed_start = datetime.fromisoformat((start_time or "").strip())
        except ValueError:
            pass
    parsed_duration = 60
    try:
        parsed_duration = int(duration_minutes)
    except (ValueError, TypeError):
        pass
    game = Game(
        name=name,
        description=description,
        is_active=(is_active == "1"),
        start_time=parsed_start,
        duration_minutes=parsed_duration,
        game_type=game_type,
    )
    db.add(game)
    db.commit()
    db.refresh(game)
    request.session.setdefault("flash", []).append(("success", "Игра успешно создана."))
    return RedirectResponse(url=f"/games/{game.id}", status_code=303)


@router.get("/{game_id:int}/edit", response_class=HTMLResponse, response_model=None)
async def game_edit_form(
    request: Request,
    game_id: int,
    current_user: Annotated[Union[User, RedirectResponse], Depends(require_admin_or_moderator)],
    db: Annotated[Session, Depends(get_db)],
):
    """Show form to edit game. Admin or moderator only. 404 if game not found."""
    logger.info("GET /games/%s/edit - User %s", game_id, _log_user(request))
    if isinstance(current_user, RedirectResponse):
        return current_user
    game = (
        db.query(Game)
        .options(selectinload(Game.teams))
        .filter(Game.id == game_id)
        .first()
    )
    if game is None:
        logger.warning("GET /games/%s/edit - Game not found - Status: 404", game_id)
        raise HTTPException(status_code=404, detail="Игра не найдена")
    all_teams = db.query(Team).order_by(Team.name).all()
    game_team_ids = [t.id for t in game.teams]
    return templates.TemplateResponse(
        "games/edit.html",
        {
            "request": request,
            "game": game,
            "all_teams": all_teams,
            "game_team_ids": game_team_ids,
            "csrf_token": get_csrf_token(request),
            "errors": {},
        },
    )


@router.post("/{game_id:int}/edit", response_class=RedirectResponse, response_model=None)
async def game_edit_submit(
    request: Request,
    game_id: int,
    current_user: Annotated[Union[User, RedirectResponse], Depends(require_admin_or_moderator)],
    db: Annotated[Session, Depends(get_db)],
):
    """Update game and assigned teams. Admin or moderator only. 404 if game not found."""
    logger.info("POST /games/%s/edit - User %s - Params: name from form, team_ids from form", game_id, _log_user(request))
    if isinstance(current_user, RedirectResponse):
        return current_user
    form_data = await request.form()
    csrf_token = form_data.get("csrf_token", "")
    validate_csrf(request, csrf_token)
    name = (form_data.get("name") or "").strip()
    description = (form_data.get("description") or "").strip() or None
    is_active = form_data.get("is_active", "0")
    team_id_strs = form_data.getlist("team_ids")
    team_ids = []
    for s in team_id_strs:
        try:
            team_ids.append(int(s))
        except (ValueError, TypeError):
            pass
    logger.debug("POST /games/%s/edit - team_ids=%s", game_id, team_ids)
    game = (
        db.query(Game)
        .options(selectinload(Game.teams))
        .filter(Game.id == game_id)
        .first()
    )
    if game is None:
        logger.warning("POST /games/%s/edit - Game not found - Status: 404", game_id)
        raise HTTPException(status_code=404, detail="Игра не найдена")
    errors = {}
    if not name:
        errors["name"] = "Название игры обязательно."
    if len(name) > 128:
        errors["name"] = "Название не должно превышать 128 символов."
    if errors:
        all_teams = db.query(Team).order_by(Team.name).all()
        return templates.TemplateResponse(
            "games/edit.html",
            {
                "request": request,
                "game": game,
                "all_teams": all_teams,
                "game_team_ids": team_ids,
                "form_name": name,
                "form_description": description or "",
                "form_is_active": is_active,
                "csrf_token": get_csrf_token(request),
                "errors": errors,
            },
            status_code=400,
        )
    game.name = name
    game.description = description
    game.is_active = (is_active == "1")

    # Sync game type
    game_type_val = (form_data.get("game_type") or "abacus").strip()
    if game_type_val in ("abacus", "five_by_five"):
        game.game_type = game_type_val
    else:
        game.game_type = "abacus"

    # Parse time fields
    start_time_str = (form_data.get("start_time") or "").strip()
    if start_time_str:
        try:
            game.start_time = datetime.fromisoformat(start_time_str)
        except ValueError:
            pass
    else:
        game.start_time = None
    dur_str = (form_data.get("duration_minutes") or "").strip()
    if dur_str:
        try:
            game.duration_minutes = int(dur_str)
        except (ValueError, TypeError):
            pass
    # Sync game teams: set of team ids that should be in game
    wanted = set(team_ids)
    current = {t.id for t in game.teams}
    for tid in wanted - current:
        db.add(GameTeam(game_id=game_id, team_id=tid))
    for tid in current - wanted:
        gt = db.query(GameTeam).filter(GameTeam.game_id == game_id, GameTeam.team_id == tid).first()
        if gt:
            db.delete(gt)
    db.commit()
    request.session.setdefault("flash", []).append(("success", "Игра обновлена."))
    logger.info("POST /games/%s/edit - Result: success - User %s - Status: 303", game_id, _log_user(request))
    return RedirectResponse(url=f"/games/{game_id}", status_code=303)


@router.get("/{game_id:int}/delete", response_class=HTMLResponse, response_model=None)
async def game_delete_confirm(
    request: Request,
    game_id: int,
    current_user: Annotated[Union[User, RedirectResponse], Depends(require_admin)],
    db: Annotated[Session, Depends(get_db)],
):
    """Show confirmation page for game deletion. Admin only. Cascade deletes topics/tasks."""
    logger.info("GET /games/%s/delete - User %s", game_id, _log_user(request))
    if isinstance(current_user, RedirectResponse):
        return current_user
    game = db.query(Game).filter(Game.id == game_id).first()
    if game is None:
        logger.warning("GET /games/%s/delete - Game not found - Status: 404", game_id)
        raise HTTPException(status_code=404, detail="Игра не найдена")
    return templates.TemplateResponse(
        "games/delete.html",
        {"request": request, "game": game, "csrf_token": get_csrf_token(request)},
    )


@router.post("/{game_id:int}/delete", response_class=RedirectResponse, response_model=None)
async def game_delete_submit(
    request: Request,
    game_id: int,
    current_user: Annotated[Union[User, RedirectResponse], Depends(require_admin)],
    db: Annotated[Session, Depends(get_db)],
    csrf_token: str = Form(""),
):
    """Delete game (cascade: topics and tasks). Admin only."""
    if isinstance(current_user, RedirectResponse):
        return current_user
    validate_csrf(request, csrf_token)
    game = db.query(Game).filter(Game.id == game_id).first()
    if game is None:
        logger.warning("POST /games/%s/delete - Game not found - Status: 404", game_id)
        raise HTTPException(status_code=404, detail="Игра не найдена")
    db.delete(game)
    db.commit()
    request.session.setdefault("flash", []).append(("success", "Игра удалена."))
    logger.info("POST /games/%s/delete - Result: success - User %s - Status: 303", game_id, _log_user(request))
    return RedirectResponse(url="/games/", status_code=303)


def _resolve_play_team(
    request: Request, user: User, game: Game, db: Session
) -> int | None:
    """Resolve which team_id to use for play/task: query param for mod, user.team_id for team."""
    if user.role in ("administrator", "moderator"):
        team_id_param = request.query_params.get("team_id")
        logger.debug("_resolve_play_team: user=%s game_id=%s query team_id=%s", user.username, game.id, team_id_param)
        if team_id_param:
            try:
                tid = int(team_id_param)
                if any(t.id == tid for t in game.teams):
                    logger.debug("_resolve_play_team: resolved team_id=%s (from query)", tid)
                    return tid
                logger.debug("_resolve_play_team: team_id=%s not in game teams - ignoring", tid)
            except ValueError:
                logger.debug("_resolve_play_team: invalid team_id param %r", team_id_param)
        return None  # moderator may choose from dropdown
    if user.team_id and any(t.id == user.team_id for t in game.teams):
        return user.team_id
    return None


@router.get("/{game_id:int}/play", response_class=HTMLResponse, response_model=None)
async def game_play(
    request: Request,
    game_id: int,
    auth: Annotated[Union[tuple[User, Game], RedirectResponse], Depends(require_game_access)],
    db: Annotated[Session, Depends(get_db)],
):
    """Game board: 6×6 topics × tasks. Access: authenticated, team in game or admin/moderator."""
    if isinstance(auth, RedirectResponse):
        return auth
    user, game = auth
    team_id_from_query = request.query_params.get("team_id")
    logger.info("GET /games/%s/play - User %s - query team_id=%s", game_id, _log_user(request), team_id_from_query)
    is_finished = getattr(game, "status", "in_progress") == "finished"
    team_id = _resolve_play_team(request, user, game, db)
    logger.info("GET /games/%s/play - resolved team_id=%s passed to template (viewing_team_id)", game_id, team_id)

    time_expired = is_game_time_expired(game)
    game_has_not_started = getattr(game, "start_time", None) is not None and datetime.utcnow() < game.start_time
    game_is_paused = is_game_paused(game)
    
    # If the game cannot be played, we pass this to the template to lock cells
    board_locked = is_finished or time_expired or game_has_not_started or game_is_paused

    end_time = get_game_end_time(game)

    if getattr(game, "game_type", "abacus") == "five_by_five":
        state = get_game_board_state_5x5(db, game_id, team_id=None if (team_id is None and user.role in ("administrator", "moderator")) else team_id)
        template_name = "games/play_5x5.html"
    else:
        state = get_game_board_state(db, game_id, team_id=None if (team_id is None and user.role in ("administrator", "moderator")) else team_id)
        template_name = "games/play.html"
        
    state["request"] = request
    state["user"] = user
    state["csrf_token"] = get_csrf_token(request)
    state["game_teams"] = game.teams
    state["viewing_team_name"] = next((t.name for t in game.teams if t.id == team_id), None) if team_id else None
    state["time_expired"] = time_expired
    state["is_finished"] = is_finished
    state["is_paused"] = game_is_paused
    state["game_has_not_started"] = game_has_not_started
    state["board_locked"] = board_locked
    state["end_time"] = end_time
    state["server_now_ts"] = int(datetime.utcnow().timestamp())
    state["end_time_ts"] = int(end_time.timestamp()) if end_time else None
    state["start_time_ts"] = int(game.start_time.timestamp()) if game.start_time else None
    return templates.TemplateResponse(template_name, state)


@router.get("/{game_id:int}/task/{task_id:int}", response_class=HTMLResponse, response_model=None)
async def game_task_page(
    request: Request,
    game_id: int,
    task_id: int,
    auth: Annotated[Union[tuple[User, Game], RedirectResponse], Depends(require_game_access)],
    db: Annotated[Session, Depends(get_db)],
):
    """Show task page for answering. Checks availability and game state."""
    if isinstance(auth, RedirectResponse):
        return auth
    user, game = auth
    team_id = _resolve_play_team(request, user, game, db)
    logger.info("GET /games/%s/task/%s - User %s - team_id=%s", game_id, task_id, _log_user(request), team_id)
    
    if getattr(game, "status", "in_progress") == "finished":
        request.session.setdefault("flash", []).append(("info", "Игра завершена."))
        return RedirectResponse(url=f"/games/{game_id}/results", status_code=303)
    
    if team_id is None:
        logger.warning("GET /games/%s/task/%s - No team selected - redirect to play", game_id, task_id)
        request.session.setdefault("flash", []).append(("warning", "Выберите команду для ответа."))
        return RedirectResponse(url=f"/games/{game_id}/play", status_code=303)
    
    ok, msg = check_task_available(db, game_id, team_id, task_id)
    if not ok:
        logger.info("GET /games/%s/task/%s - Task not available for team_id=%s: %s - Status: 303", game_id, task_id, team_id, msg)
        request.session.setdefault("flash", []).append(("danger", msg))
        return RedirectResponse(url=f"/games/{game_id}/play?team_id={team_id}", status_code=303)
    
    task = (
        db.query(Task)
        .options(selectinload(Task.topic))
        .filter(Task.id == task_id)
        .first()
    )
    if task is None:
        raise HTTPException(status_code=404, detail="Задание не найдено")
    
    return templates.TemplateResponse(
        "games/task.html",
        {
            "request": request,
            "game": game,
            "task": task,
            "topic": task.topic,
            "user": user,
            "team_id": team_id,
            "csrf_token": get_csrf_token(request),
        },
    )


@router.post("/{game_id:int}/task/{task_id:int}", response_class=RedirectResponse, response_model=None)
async def game_task_submit(
    request: Request,
    game_id: int,
    task_id: int,
    auth: Annotated[Union[tuple[User, Game], RedirectResponse], Depends(require_game_access)],
    db: Annotated[Session, Depends(get_db)],
    answer_text: str = Form(""),
    csrf_token: str = Form(""),
):
    """Submit answer for a task. Validates, scores, and updates result."""
    if isinstance(auth, RedirectResponse):
        return auth
    user, game = auth
    validate_csrf(request, csrf_token)
    
    team_id = _resolve_play_team(request, user, game, db)
    if team_id is None:
        request.session.setdefault("flash", []).append(("warning", "Выберите команду для ответа."))
        return RedirectResponse(url=f"/games/{game_id}/play", status_code=303)
    
    if getattr(game, "game_type", "abacus") == "five_by_five":
        submit_answer_5x5(db, game_id, team_id, task_id, answer_text.strip())
    else:
        svc_submit_answer(db, game_id, team_id, task_id, answer_text.strip())
    
    db.commit()
    request.session.setdefault("flash", []).append(("success", "Ответ отправлен!"))
    return RedirectResponse(url=f"/games/{game_id}/play?team_id={team_id}", status_code=303)


@router.get("/{game_id:int}/results", response_class=HTMLResponse, response_model=None)
async def game_results(
    request: Request,
    game_id: int,
    db: Annotated[Session, Depends(get_db)],
):
    """Show results for a game."""
    logger.info("GET /games/%s/results - User %s", game_id, _log_user(request))
    game = db.query(Game).filter(Game.id == game_id).first()
    if game is None:
        raise HTTPException(status_code=404, detail="Игра не найдена")
    
    results = (
        db.query(Result)
        .options(selectinload(Result.team))
        .filter(Result.game_id == game_id)
        .order_by(Result.total_score.desc())
        .all()
    )
    
    user = getattr(request.state, "user", None)
    return templates.TemplateResponse(
        "games/results.html",
        {
            "request": request,
            "game": game,
            "results": results,
            "can_manage": _can_manage_games(user),
        },
    )


@router.get("/{game_id:int}/topics", response_class=HTMLResponse, response_model=None)
async def game_topics_list(
    request: Request,
    game_id: int,
    current_user: Annotated[Union[User, RedirectResponse], Depends(require_admin_or_moderator)],
    db: Annotated[Session, Depends(get_db)],
):
    """Show topics list for a game. Admin or moderator only."""
    if isinstance(current_user, RedirectResponse):
        return current_user
    
    logger.info("GET /games/%s/topics - User %s", game_id, _log_user(request))
    game = (
        db.query(Game)
        .options(selectinload(Game.game_topics).selectinload(GameTopic.topic))
        .options(selectinload(Game.game_topics).selectinload(GameTopic.game_tasks))
        .filter(Game.id == game_id)
        .first()
    )
    if game is None:
        raise HTTPException(status_code=404, detail="Игра не найдена")
    
    topics_slots = _get_game_topics(game)
    
    return templates.TemplateResponse(
        "games/topics.html",
        {
            "request": request,
            "game": game,
            "topics_slots": topics_slots,
            "csrf_token": get_csrf_token(request),
        },
    )


@router.get("/{game_id:int}/topics/{topic_index:int}/edit", response_class=HTMLResponse, response_model=None)
async def game_topic_edit_form(
    request: Request,
    game_id: int,
    topic_index: int,
    current_user: Annotated[Union[User, RedirectResponse], Depends(require_admin_or_moderator)],
    db: Annotated[Session, Depends(get_db)],
):
    """Show topic edit form for a specific slot. Admin or moderator only."""
    if isinstance(current_user, RedirectResponse):
        return current_user
    
    logger.info("GET /games/%s/topics/%s/edit - User %s", game_id, topic_index, _log_user(request))
    
    game = db.query(Game).filter(Game.id == game_id).first()
    if game is None:
        raise HTTPException(status_code=404, detail="Игра не найдена")
    
    n_topics = get_num_topics(game)
    n_tasks = get_num_tasks(game)
    
    if not (1 <= topic_index <= n_topics):
        raise HTTPException(status_code=404, detail="Недопустимый номер темы")
    
    # Get or create GameTopic for this slot
    game_topic = db.query(GameTopic).filter(
        GameTopic.game_id == game_id,
        GameTopic.order_index == topic_index
    ).first()
    
    # Get all available topics from bank
    all_topics = db.query(Topic).order_by(Topic.title).all()
    
    # Get tasks for this game topic if it exists
    tasks_slots = []
    if game_topic:
        tasks_slots = _get_game_tasks(game, game_topic)
    
    # Get all available tasks grouped by topic
    all_tasks_by_topic = {}
    for topic in all_topics:
        tasks = db.query(Task).filter(Task.topic_id == topic.id).order_by(Task.points).all()
        all_tasks_by_topic[topic.id] = tasks
    
    return templates.TemplateResponse(
        "games/topic_edit.html",
        {
            "request": request,
            "game": game,
            "topic_index": topic_index,
            "game_topic": game_topic,
            "tasks_slots": tasks_slots,
            "all_topics": all_topics,
            "all_tasks_by_topic": all_tasks_by_topic,
            "n_tasks": n_tasks,
            "csrf_token": get_csrf_token(request),
        },
    )


@router.post("/{game_id:int}/topics/{topic_index:int}/edit", response_class=RedirectResponse, response_model=None)
async def game_topic_edit_submit(
    request: Request,
    game_id: int,
    topic_index: int,
    current_user: Annotated[Union[User, RedirectResponse], Depends(require_admin_or_moderator)],
    db: Annotated[Session, Depends(get_db)],
):
    """Save topic and tasks for a slot. Admin or moderator only."""
    if isinstance(current_user, RedirectResponse):
        return current_user
    
    validate_csrf(request, (await request.form()).get("csrf_token", ""))
    
    game = db.query(Game).filter(Game.id == game_id).first()
    if game is None:
        raise HTTPException(status_code=404, detail="Игра не найдена")
    
    n_topics = get_num_topics(game)
    n_tasks = get_num_tasks(game)
    
    if not (1 <= topic_index <= n_topics):
        raise HTTPException(status_code=404, detail="Недопустимый номер темы")
    
    form_data = await request.form()
    topic_id = form_data.get("topic_id")
    
    if not topic_id:
        request.session.setdefault("flash", []).append(("danger", "Выберите тему из банка."))
        return RedirectResponse(url=f"/games/{game_id}/topics/{topic_index}/edit", status_code=303)
    
    try:
        topic_id = int(topic_id)
    except (ValueError, TypeError):
        request.session.setdefault("flash", []).append(("danger", "Некорректный ID темы."))
        return RedirectResponse(url=f"/games/{game_id}/topics/{topic_index}/edit", status_code=303)
    
    # Get or create GameTopic
    game_topic = db.query(GameTopic).filter(
        GameTopic.game_id == game_id,
        GameTopic.order_index == topic_index
    ).first()
    
    if game_topic is None:
        game_topic = GameTopic(game_id=game_id, topic_id=topic_id, order_index=topic_index)
        db.add(game_topic)
    else:
        game_topic.topic_id = topic_id
    
    db.flush()
    
    # Delete old tasks for this slot
    db.query(GameTask).filter(GameTask.game_topic_id == game_topic.id).delete()
    
    # Add new tasks
    for i in range(1, n_tasks + 1):
        task_id = form_data.get(f"task_{i}")
        if task_id:
            try:
                task_id = int(task_id)
                db.add(GameTask(game_topic_id=game_topic.id, task_id=task_id, order_index=i))
            except (ValueError, TypeError):
                pass
    
    db.commit()
    request.session.setdefault("flash", []).append(("success", "Тема и задания сохранены."))
    return RedirectResponse(url=f"/games/{game_id}/topics", status_code=303)


@router.get("/{game_id:int}/answers", response_class=HTMLResponse, response_model=None)
async def game_answers_list(
    request: Request,
    game_id: int,
    current_user: Annotated[Union[User, RedirectResponse], Depends(require_admin_or_moderator)],
    db: Annotated[Session, Depends(get_db)],
):
    """Show all answers for a game. Admin or moderator only."""
    if isinstance(current_user, RedirectResponse):
        return current_user
    
    logger.info("GET /games/%s/answers - User %s", game_id, _log_user(request))
    game = db.query(Game).filter(Game.id == game_id).first()
    if game is None:
        raise HTTPException(status_code=404, detail="Игра не найдена")
    
    answers = (
        db.query(Answer)
        .join(Result)
        .options(selectinload(Answer.task))
        .options(selectinload(Answer.result).selectinload(Result.team))
        .filter(Result.game_id == game_id)
        .order_by(Answer.submitted_at.desc())
        .all()
    )
    
    return templates.TemplateResponse(
        "games/answers.html",
        {
            "request": request,
            "game": game,
            "answers": answers,
            "csrf_token": get_csrf_token(request),
        },
    )


@router.post("/{game_id:int}/answers/{answer_id:int}/toggle", response_class=RedirectResponse, response_model=None)
async def game_answer_toggle(
    request: Request,
    game_id: int,
    answer_id: int,
    current_user: Annotated[Union[User, RedirectResponse], Depends(require_admin_or_moderator)],
    db: Annotated[Session, Depends(get_db)],
    csrf_token: str = Form(""),
):
    """Toggle answer correctness and recalculate scores. Admin or moderator only."""
    if isinstance(current_user, RedirectResponse):
        return current_user
    
    validate_csrf(request, csrf_token)
    
    answer = (
        db.query(Answer)
        .options(selectinload(Answer.result))
        .options(selectinload(Answer.task))
        .filter(Answer.id == answer_id)
        .first()
    )
    if answer is None:
        raise HTTPException(status_code=404, detail="Ответ не найден")
    
    if answer.result.game_id != game_id:
        raise HTTPException(status_code=400, detail="Ответ не принадлежит данной игре")
    
    answer.is_correct = not answer.is_correct
    answer.base_points_awarded = answer.task.points if answer.is_correct else 0
    db.flush()
    
    from sqlalchemy import func as sqlfunc
    result = answer.result
    result.score_base = int(
        db.query(sqlfunc.coalesce(sqlfunc.sum(Answer.base_points_awarded), 0))
        .filter(Answer.result_id == result.id)
        .scalar()
        or 0
    )
    
    game = db.query(Game).filter(Game.id == game_id).first()
    if game and getattr(game, "game_type", "abacus") == "five_by_five":
        _recalculate_bonuses_5x5(db, game_id)
    else:
        _recalculate_bonuses(db, game_id)
    
    db.commit()
    status_text = "верный" if answer.is_correct else "неверный"
    request.session.setdefault("flash", []).append(("success", f"Ответ отмечен как {status_text}. Баллы пересчитаны."))
    return RedirectResponse(url=f"/games/{game_id}/answers", status_code=303)


@router.post("/{game_id:int}/pause", response_class=RedirectResponse, response_model=None)
async def game_pause(
    request: Request,
    game_id: int,
    current_user: Annotated[Union[User, RedirectResponse], Depends(require_admin_or_moderator)],
    db: Annotated[Session, Depends(get_db)],
    csrf_token: str = Form(""),
):
    """Pause the game: set status=paused, record paused_at timestamp."""
    if isinstance(current_user, RedirectResponse):
        return current_user
    
    validate_csrf(request, csrf_token)
    game = db.query(Game).filter(Game.id == game_id).first()
    if game is None:
        raise HTTPException(status_code=404, detail="Игра не найдена")
    
    game.status = "paused"
    game.paused_at = datetime.utcnow()
    db.commit()
    
    request.session.setdefault("flash", []).append(("success", "Игра приостановлена."))
    return RedirectResponse(url=f"/games/{game_id}", status_code=303)


@router.post("/{game_id:int}/resume", response_class=RedirectResponse, response_model=None)
async def game_resume(
    request: Request,
    game_id: int,
    current_user: Annotated[Union[User, RedirectResponse], Depends(require_admin_or_moderator)],
    db: Annotated[Session, Depends(get_db)],
    csrf_token: str = Form(""),
):
    """Resume the game: set status=in_progress, adjust start_time for paused duration."""
    if isinstance(current_user, RedirectResponse):
        return current_user
    
    validate_csrf(request, csrf_token)
    game = db.query(Game).filter(Game.id == game_id).first()
    if game is None:
        raise HTTPException(status_code=404, detail="Игра не найдена")
    
    if game.status == "paused" and game.paused_at:
        pause_duration = datetime.utcnow() - game.paused_at
        if game.start_time:
            game.start_time = game.start_time + pause_duration
    
    game.status = "in_progress"
    game.paused_at = None
    db.commit()
    
    request.session.setdefault("flash", []).append(("success", "Игра возобновлена."))
    return RedirectResponse(url=f"/games/{game_id}", status_code=303)


@router.post("/{game_id:int}/finish", response_class=RedirectResponse, response_model=None)
async def game_finish(
    request: Request,
    game_id: int,
    current_user: Annotated[Union[User, RedirectResponse], Depends(require_admin_or_moderator)],
    db: Annotated[Session, Depends(get_db)],
    csrf_token: str = Form(""),
):
    """Manually finish the game: set status=finished, compute final scores."""
    if isinstance(current_user, RedirectResponse):
        return current_user
    
    validate_csrf(request, csrf_token)
    game = db.query(Game).filter(Game.id == game_id).first()
    if game is None:
        raise HTTPException(status_code=404, detail="Игра не найдена")
    
    svc_finish_game(db, game_id)
    db.commit()
    
    request.session.setdefault("flash", []).append(("success", "Игра завершена."))
    return RedirectResponse(url=f"/games/{game_id}/results", status_code=303)
