"""
Game routes: list games, game detail, and CRUD (create, edit, delete).

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
from app.deps import (
    get_csrf_token,
    require_admin,
    require_admin_or_moderator,
    require_game_access,
    require_authenticated,
    validate_csrf,
)
from app.models import Game, GameTeam, Result, Task, Team, Topic, User
from app.services.game_service import (
    check_task_available,
    finish_game as svc_finish_game,
    get_game_board_state,
    submit_answer as svc_submit_answer,
)

logger = logging.getLogger(__name__)


def _log_user(request: Request) -> str:
    """Return 'username (id=X)' or 'anonymous' for logging."""
    user = getattr(request.state, "user", None)
    if user is None:
        return "anonymous"
    return f"{user.username} (id={user.id}, role={user.role})"


# Abacus: exactly 6 topics per game, 6 tasks per topic; default points 10–60
NUM_TOPICS = 6
NUM_TASKS_PER_TOPIC = 6
DEFAULT_POINTS = [10, 20, 30, 40, 50, 60]


def _ensure_game_topics(db: Session, game: Game) -> list[Topic]:
    """Ensure the game has exactly 6 topics; create placeholders if missing. Returns topics ordered by order_index."""
    existing = {t.order_index: t for t in db.query(Topic).filter(Topic.game_id == game.id).all()}
    for i in range(1, NUM_TOPICS + 1):
        if i not in existing:
            t = Topic(game_id=game.id, title=f"Тема {i}", order_index=i)
            db.add(t)
    db.commit()
    db.refresh(game)
    return sorted(game.topics, key=lambda t: t.order_index)


def _ensure_topic_tasks(db: Session, topic: Topic) -> list[Task]:
    """Ensure the topic has exactly 6 tasks; create placeholders if missing. Returns tasks ordered by order_index."""
    existing = {t.order_index: t for t in topic.tasks}
    for i in range(1, NUM_TASKS_PER_TOPIC + 1):
        if i not in existing:
            task = Task(
                topic_id=topic.id,
                text="",
                order_index=i,
                points=DEFAULT_POINTS[i - 1],
                correct_answer="",
            )
            db.add(task)
    db.commit()
    db.refresh(topic)
    return sorted(topic.tasks, key=lambda t: t.order_index)

router = APIRouter(prefix="/games", tags=["games"])
templates = Jinja2Templates(
    directory=str(Path(__file__).resolve().parent.parent.parent / "templates")
)


def _can_manage_games(user: User | None) -> bool:
    """Return True if user can create/edit games (admin or moderator)."""
    return user is not None and user.role in ("admin", "moderator")


def _can_delete_games(user: User | None) -> bool:
    """Return True if user can delete games (admin only)."""
    return user is not None and user.role == "admin"


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


@router.get("/create", response_class=HTMLResponse, response_model=None)
async def game_create_form(
    request: Request,
    current_user: Annotated[Union[User, RedirectResponse], Depends(require_admin_or_moderator)],
    db: Annotated[Session, Depends(get_db)],
) -> Union[HTMLResponse, RedirectResponse]:
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
    is_active: str = Form("0"),  # 0 = draft, 1 = active
    csrf_token: str = Form(""),
) -> Union[RedirectResponse, HTMLResponse]:
    """Create a new game. Admin or moderator only. Default status: draft."""
    logger.info("POST /games/create - User %s - name=%r is_active=%s", _log_user(request), name, is_active)
    if isinstance(current_user, RedirectResponse):
        return current_user
    validate_csrf(request, csrf_token)
    name = (name or "").strip()
    description = (description or "").strip() or None
    errors = {}
    if not name:
        errors["name"] = "Название игры обязательно."
    if len(name) > 128:
        errors["name"] = "Название не должно превышать 128 символов."
    if errors:
        logger.warning("POST /games/create - validation errors: %s - Status: 400", errors)
        return templates.TemplateResponse(
            "games/create.html",
            {
                "request": request,
                "csrf_token": get_csrf_token(request),
                "game": {"name": name, "description": description or ""},
                "is_active": is_active,
                "errors": errors,
            },
            status_code=400,
        )
    game = Game(
        name=name,
        description=description,
        is_active=(is_active == "1"),
    )
    db.add(game)
    db.commit()
    db.refresh(game)
    request.session.setdefault("flash", []).append(("success", "Игра успешно создана."))
    logger.info("POST /games/create - Game created: id=%s name=%s - User %s - Result: success - Status: 303", game.id, game.name, _log_user(request))
    return RedirectResponse(url=f"/games/{game.id}", status_code=303)


@router.get("/{game_id:int}/edit", response_class=HTMLResponse, response_model=None)
async def game_edit_form(
    request: Request,
    game_id: int,
    current_user: Annotated[Union[User, RedirectResponse], Depends(require_admin_or_moderator)],
    db: Annotated[Session, Depends(get_db)],
) -> Union[HTMLResponse, RedirectResponse]:
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
) -> Union[RedirectResponse, HTMLResponse]:
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
) -> Union[HTMLResponse, RedirectResponse]:
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
) -> Union[RedirectResponse, HTMLResponse]:
    """Delete game (cascade: topics and tasks). Admin only."""
    if isinstance(current_user, RedirectResponse):
        return current_user
    validate_csrf(request, csrf_token)
    game = (
        db.query(Game)
        .options(
            selectinload(Game.topics).selectinload(Topic.tasks),
        )
        .filter(Game.id == game_id)
        .first()
    )
    if game is None:
        logger.warning("POST /games/%s/delete - Game not found - Status: 404", game_id)
        raise HTTPException(status_code=404, detail="Игра не найдена")
    # Delete all topics and their tasks first (avoids NOT NULL constraint on topics.game_id)
    for topic in game.topics:
        for task in topic.tasks:
            db.delete(task)
        db.delete(topic)
    db.flush()
    db.delete(game)
    db.commit()
    request.session.setdefault("flash", []).append(("success", "Игра удалена."))
    logger.info("POST /games/%s/delete - Result: success - User %s - Status: 303", game_id, _log_user(request))
    return RedirectResponse(url="/games/", status_code=303)


def _resolve_play_team(
    request: Request, user: User, game: Game, db: Session
) -> int | None:
    """Resolve which team_id to use for play/task: query param for mod, user.team_id for team."""
    if user.role in ("admin", "moderator"):
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
) -> Union[HTMLResponse, RedirectResponse]:
    """Game board: 6×6 topics × tasks. Access: authenticated, team in game or admin/moderator."""
    if isinstance(auth, RedirectResponse):
        return auth
    user, game = auth
    team_id_from_query = request.query_params.get("team_id")
    logger.info("GET /games/%s/play - User %s - query team_id=%s", game_id, _log_user(request), team_id_from_query)
    if getattr(game, "status", "in_progress") == "finished":
        request.session.setdefault("flash", []).append(
            ("info", "Игра завершена. Доступны только результаты.")
        )
        return RedirectResponse(url=f"/games/{game_id}/results", status_code=303)
    # Ensure game has 6 topics and 6 tasks per topic for board display
    _ensure_game_topics(db, game)
    for topic in sorted(game.topics, key=lambda t: t.order_index):
        _ensure_topic_tasks(db, topic)
    db.refresh(game)
    team_id = _resolve_play_team(request, user, game, db)
    logger.info("GET /games/%s/play - resolved team_id=%s passed to template (viewing_team_id)", game_id, team_id)
    if team_id is None and user.role in ("admin", "moderator"):
        # Show board without a selected team (scores only); team selector in template
        state = get_game_board_state(db, game_id, team_id=None)
        logger.debug("GET /games/%s/play - Board loaded with no team (admin/moderator) - tasks all locked for view", game_id)
    else:
        state = get_game_board_state(db, game_id, team_id=team_id)
        num_topics = len(state.get("topic_rows", []))
        num_cells = sum(len(r.get("tasks", [])) for r in state.get("topic_rows", []))
        logger.info("GET /games/%s/play - Board loaded: team_id=%s, %s topics, %s tasks - Status: 200", game_id, team_id, num_topics, num_cells)
    state["request"] = request
    state["user"] = user
    state["csrf_token"] = get_csrf_token(request)
    state["game_teams"] = game.teams  # for moderator team dropdown
    state["viewing_team_name"] = next((t.name for t in game.teams if t.id == team_id), None) if team_id else None
    return templates.TemplateResponse("games/play.html", state)


@router.get("/{game_id:int}/task/{task_id:int}", response_class=HTMLResponse, response_model=None)
async def game_task_page(
    request: Request,
    game_id: int,
    task_id: int,
    auth: Annotated[Union[tuple[User, Game], RedirectResponse], Depends(require_game_access)],
    db: Annotated[Session, Depends(get_db)],
) -> Union[HTMLResponse, RedirectResponse]:
    """Task page: show task text and answer form. Enforce order within topic."""
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
        logger.warning("GET /games/%s/task/%s - Task not found - Status: 404", game_id, task_id)
        raise HTTPException(status_code=404, detail="Задание не найдено")
    topic = task.topic
    if topic is None or topic.game_id != game_id:
        logger.warning("GET /games/%s/task/%s - Task not in game - Status: 404", game_id, task_id)
        raise HTTPException(status_code=404, detail="Задание не найдено")
    logger.info("GET /games/%s/task/%s - Task page rendered - team_id=%s - Status: 200", game_id, task_id, team_id)
    return templates.TemplateResponse(
        "games/task.html",
        {
            "request": request,
            "game": game,
            "topic": topic,
            "task": task,
            "team_id": team_id,
            "game_teams": game.teams,
            "user": user,
            "csrf_token": get_csrf_token(request),
        },
    )


@router.post("/{game_id:int}/task/{task_id:int}/answer", response_class=RedirectResponse, response_model=None)
async def game_task_submit_answer(
    request: Request,
    game_id: int,
    task_id: int,
    auth: Annotated[Union[tuple[User, Game], RedirectResponse], Depends(require_game_access)],
    db: Annotated[Session, Depends(get_db)],
    team_id: int = Form(...),
    submitted_answer: str = Form(""),
    csrf_token: str = Form(""),
) -> Union[RedirectResponse, HTMLResponse]:
    """Submit answer. team_id from form (moderator) or must match user's team."""
    if isinstance(auth, RedirectResponse):
        return auth
    user, game = auth
    logger.info("POST /games/%s/task/%s/answer - User %s - team_id=%s answer=%r", game_id, task_id, _log_user(request), team_id, (submitted_answer[:20] + "..." if len(submitted_answer or "") > 20 else submitted_answer))
    validate_csrf(request, csrf_token)
    if getattr(game, "status", "in_progress") == "finished":
        request.session.setdefault("flash", []).append(("info", "Игра завершена."))
        return RedirectResponse(url=f"/games/{game_id}/results", status_code=303)
    # Resolve effective team: team must be in game; team user can only submit for their team
    in_game = db.query(GameTeam).filter(GameTeam.game_id == game_id, GameTeam.team_id == team_id).first()
    if not in_game:
        logger.warning("POST /games/%s/task/%s/answer - Team %s not in game - Status: 303", game_id, task_id, team_id)
        request.session.setdefault("flash", []).append(("danger", "Команда не участвует в игре."))
        return RedirectResponse(url=f"/games/{game_id}/play", status_code=303)
    if user.role not in ("admin", "moderator") and user.team_id != team_id:
        logger.warning("POST /games/%s/task/%s/answer - User cannot submit for team %s - Status: 303", game_id, task_id, team_id)
        request.session.setdefault("flash", []).append(("danger", "Нельзя отвечать за другую команду."))
        return RedirectResponse(url=f"/games/{game_id}/play", status_code=303)
    success, message, is_correct = svc_submit_answer(db, game_id, team_id, task_id, submitted_answer)
    if not success:
        logger.info("POST /games/%s/task/%s/answer - Validation failed: %s - Status: 303", game_id, task_id, message)
        request.session.setdefault("flash", []).append(("danger", message))
    else:
        logger.info("POST /games/%s/task/%s/answer - Correct=%s - %s - User %s - Status: 303", game_id, task_id, is_correct, message, _log_user(request))
        request.session.setdefault("flash", []).append(
            ("success" if is_correct else "info", message)
        )
    return RedirectResponse(url=f"/games/{game_id}/play?team_id={team_id}", status_code=303)


@router.post("/{game_id:int}/finish", response_class=RedirectResponse, response_model=None)
async def game_finish(
    request: Request,
    game_id: int,
    current_user: Annotated[Union[User, RedirectResponse], Depends(require_admin_or_moderator)],
    db: Annotated[Session, Depends(get_db)],
    csrf_token: str = Form(""),
) -> Union[RedirectResponse, HTMLResponse]:
    """End game (admin/moderator only). Set status to finished, redirect to results."""
    logger.info("POST /games/%s/finish - User %s", game_id, _log_user(request))
    if isinstance(current_user, RedirectResponse):
        return current_user
    validate_csrf(request, csrf_token)
    game = db.query(Game).filter(Game.id == game_id).first()
    if game is None:
        logger.warning("POST /games/%s/finish - Game not found - Status: 404", game_id)
        raise HTTPException(status_code=404, detail="Игра не найдена")
    svc_finish_game(db, game_id)
    request.session.setdefault("flash", []).append(("success", "Игра завершена. Результаты сохранены."))
    logger.info("POST /games/%s/finish - Result: success - Status: 303", game_id)
    return RedirectResponse(url=f"/games/{game_id}/results", status_code=303)


@router.get("/{game_id:int}/results", response_class=HTMLResponse, response_model=None)
async def game_results(
    request: Request,
    game_id: int,
    db: Annotated[Session, Depends(get_db)],
) -> HTMLResponse:
    """Final leaderboard: teams, base points, bonuses, final score, rank."""
    logger.info("GET /games/%s/results - User %s", game_id, _log_user(request))
    game = db.query(Game).filter(Game.id == game_id).first()
    if game is None:
        logger.warning("GET /games/%s/results - Game not found - Status: 404", game_id)
        raise HTTPException(status_code=404, detail="Игра не найдена")

    results = (
        db.query(Result)
        .options(selectinload(Result.team))
        .filter(Result.game_id == game_id)
        .all()
    )
    # Sort by total_score desc, assign rank
    results.sort(key=lambda r: (-r.total_score, r.team.name))
    leaderboard = [
        {
            "rank": i + 1,
            "team_name": r.team.name,
            "score_base": r.score_base,
            "score_horizontal_bonus": r.score_horizontal_bonus,
            "score_vertical_bonus": r.score_vertical_bonus,
            "superbonus_multiplier": getattr(r, "superbonus_multiplier", 1.0),
            "total_score": r.total_score,
        }
        for i, r in enumerate(results)
    ]
    return templates.TemplateResponse(
        "games/results.html",
        {
            "request": request,
            "game": game,
            "leaderboard": leaderboard,
        },
    )


@router.get("/{game_id:int}/topics", response_class=HTMLResponse, response_model=None)
async def game_topics_list(
    request: Request,
    game_id: int,
    current_user: Annotated[Union[User, RedirectResponse], Depends(require_admin_or_moderator)],
    db: Annotated[Session, Depends(get_db)],
) -> Union[HTMLResponse, RedirectResponse]:
    """List all 6 topics for the game; ensure placeholders exist. Admin or moderator only."""
    logger.info("GET /games/%s/topics - User %s", game_id, _log_user(request))
    if isinstance(current_user, RedirectResponse):
        return current_user
    game = db.query(Game).filter(Game.id == game_id).first()
    if game is None:
        logger.warning("GET /games/%s/topics - Game not found - Status: 404", game_id)
        raise HTTPException(status_code=404, detail="Игра не найдена")
    topics = _ensure_game_topics(db, game)
    # Ensure each topic has 6 tasks for display
    for topic in topics:
        _ensure_topic_tasks(db, topic)
    return templates.TemplateResponse(
        "games/topics.html",
        {"request": request, "game": game, "topics": topics},
    )


@router.get("/{game_id:int}/topics/{topic_index:int}/edit", response_class=HTMLResponse, response_model=None)
async def game_topic_edit_form(
    request: Request,
    game_id: int,
    topic_index: int,
    current_user: Annotated[Union[User, RedirectResponse], Depends(require_admin_or_moderator)],
    db: Annotated[Session, Depends(get_db)],
) -> Union[HTMLResponse, RedirectResponse]:
    """Edit one topic (title + 6 tasks). topic_index 1–6. Admin or moderator only."""
    logger.info("GET /games/%s/topics/%s/edit - User %s", game_id, topic_index, _log_user(request))
    if isinstance(current_user, RedirectResponse):
        return current_user
    if not (1 <= topic_index <= NUM_TOPICS):
        raise HTTPException(status_code=404, detail="Недопустимый номер темы")
    game = db.query(Game).filter(Game.id == game_id).first()
    if game is None:
        logger.warning("GET /games/%s/topics/%s/edit - Game not found - Status: 404", game_id, topic_index)
        raise HTTPException(status_code=404, detail="Игра не найдена")
    topics = _ensure_game_topics(db, game)
    topic = next((t for t in topics if t.order_index == topic_index), None)
    if topic is None:
        raise HTTPException(status_code=404, detail="Тема не найдена")
    tasks = _ensure_topic_tasks(db, topic)
    return templates.TemplateResponse(
        "games/topic_edit.html",
        {
            "request": request,
            "game": game,
            "topic": topic,
            "tasks": tasks,
            "csrf_token": get_csrf_token(request),
            "errors": {},
            "default_points": DEFAULT_POINTS,
        },
    )


@router.post("/{game_id:int}/topics/{topic_index:int}/edit", response_class=RedirectResponse, response_model=None)
async def game_topic_edit_submit(
    request: Request,
    game_id: int,
    topic_index: int,
    current_user: Annotated[Union[User, RedirectResponse], Depends(require_admin_or_moderator)],
    db: Annotated[Session, Depends(get_db)],
    topic_title: str = Form(""),
    csrf_token: str = Form(""),
    task_1_text: str = Form(""),
    task_1_correct_answer: str = Form(""),
    task_1_points: int = Form(10),
    task_2_text: str = Form(""),
    task_2_correct_answer: str = Form(""),
    task_2_points: int = Form(20),
    task_3_text: str = Form(""),
    task_3_correct_answer: str = Form(""),
    task_3_points: int = Form(30),
    task_4_text: str = Form(""),
    task_4_correct_answer: str = Form(""),
    task_4_points: int = Form(40),
    task_5_text: str = Form(""),
    task_5_correct_answer: str = Form(""),
    task_5_points: int = Form(50),
    task_6_text: str = Form(""),
    task_6_correct_answer: str = Form(""),
    task_6_points: int = Form(60),
) -> Union[RedirectResponse, HTMLResponse]:
    """Save topic title and 6 tasks. Admin or moderator only."""
    logger.info("POST /games/%s/topics/%s/edit - User %s", game_id, topic_index, _log_user(request))
    if isinstance(current_user, RedirectResponse):
        return current_user
    validate_csrf(request, csrf_token)
    if not (1 <= topic_index <= NUM_TOPICS):
        raise HTTPException(status_code=404, detail="Недопустимый номер темы")
    game = db.query(Game).filter(Game.id == game_id).first()
    if game is None:
        logger.warning("POST /games/%s/topics/%s/edit - Game not found - Status: 404", game_id, topic_index)
        raise HTTPException(status_code=404, detail="Игра не найдена")
    topic = db.query(Topic).filter(Topic.game_id == game_id, Topic.order_index == topic_index).first()
    if topic is None:
        logger.warning("POST /games/%s/topics/%s/edit - Topic not found - Status: 404", game_id, topic_index)
        raise HTTPException(status_code=404, detail="Тема не найдена")
    tasks = _ensure_topic_tasks(db, topic)
    title = (topic_title or "").strip()
    errors = {}
    if not title:
        errors["topic_title"] = "Название темы обязательно."
    if len(title) > 256:
        errors["topic_title"] = "Название не должно превышать 256 символов."
    task_data = [
        (task_1_text, task_1_correct_answer, task_1_points),
        (task_2_text, task_2_correct_answer, task_2_points),
        (task_3_text, task_3_correct_answer, task_3_points),
        (task_4_text, task_4_correct_answer, task_4_points),
        (task_5_text, task_5_correct_answer, task_5_points),
        (task_6_text, task_6_correct_answer, task_6_points),
    ]
    for i, (text, ans, pts) in enumerate(task_data):
        if not (text or "").strip():
            errors[f"task_{i+1}_text"] = "Текст задания обязателен."
        if not (ans or "").strip():
            errors[f"task_{i+1}_correct_answer"] = "Правильный ответ обязателен."
        if not (10 <= pts <= 60):
            errors[f"task_{i+1}_points"] = "Баллы должны быть от 10 до 60."
    if errors:
        # Rebuild tasks list with submitted values for re-display (use simple objects for template)
        class _TaskRow:
            __slots__ = ("order_index", "text", "correct_answer", "points")
            def __init__(self, order_index: int, text: str, correct_answer: str, points: int):
                self.order_index = order_index
                self.text = text
                self.correct_answer = correct_answer
                self.points = points
        submitted_tasks = [
            _TaskRow(i + 1, task_data[i][0], task_data[i][1], task_data[i][2])
            for i in range(6)
        ]
        return templates.TemplateResponse(
            "games/topic_edit.html",
            {
                "request": request,
                "game": game,
                "topic": topic,
                "tasks": submitted_tasks,
                "form_title": title or topic.title,
                "csrf_token": get_csrf_token(request),
                "errors": errors,
                "default_points": DEFAULT_POINTS,
            },
            status_code=400,
        )
    topic.title = title
    for i, (text, ans, pts) in enumerate(task_data):
        if i < len(tasks):
            tasks[i].text = (text or "").strip()
            tasks[i].correct_answer = (ans or "").strip()
            tasks[i].points = max(10, min(60, pts))
    db.commit()
    request.session.setdefault("flash", []).append(("success", "Тема и задания сохранены."))
    logger.info("Game topic updated: game_id=%s topic_index=%s by user_id=%s", game_id, topic_index, current_user.id)
    return RedirectResponse(url=f"/games/{game_id}/topics", status_code=303)


@router.get("/{game_id:int}", response_class=HTMLResponse)
async def game_detail(
    request: Request,
    game_id: int,
    db: Annotated[Session, Depends(get_db)],
) -> HTMLResponse:
    """Show game detail with topics and task counts. Returns 404 if game not found."""
    logger.info("GET /games/%s - User %s", game_id, _log_user(request))
    game = (
        db.query(Game)
        .options(
            selectinload(Game.topics).selectinload(Topic.tasks),
        )
        .filter(Game.id == game_id)
        .first()
    )
    if game is None:
        logger.warning("GET /games/%s - Game not found - Status: 404", game_id)
        raise HTTPException(status_code=404, detail="Игра не найдена")
    topics = sorted(game.topics, key=lambda t: t.order_index)
    user = getattr(request.state, "user", None)
    return templates.TemplateResponse(
        "games/detail.html",
        {
            "request": request,
            "game": game,
            "topics": topics,
            "can_manage": _can_manage_games(user),
            "can_delete": _can_delete_games(user),
            "csrf_token": get_csrf_token(request),
        },
    )
