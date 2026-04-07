"""
Topic routes: bank of reusable topics and tasks.
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
from app.deps import get_csrf_token, require_admin_or_moderator, validate_csrf
from app.models import Task, Topic, User, GameTopic, GameTask

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/topics", tags=["topics"])
templates = Jinja2Templates(
    directory=str(Path(__file__).resolve().parent.parent.parent / "templates")
)

def _log_user(request: Request) -> str:
    user = getattr(request.state, "user", None)
    if user is None:
        return "anonymous"
    return f"{user.username} (id={user.id}, role={user.role})"

@router.get("", response_class=HTMLResponse, response_model=None)
@router.get("/", response_class=HTMLResponse, response_model=None)
async def topics_list(
    request: Request,
    current_user: Annotated[Union[User, RedirectResponse], Depends(require_admin_or_moderator)],
    db: Annotated[Session, Depends(get_db)],
):
    """List all topics in the bank."""
    if isinstance(current_user, RedirectResponse):
        return current_user
    topics = db.query(Topic).order_by(Topic.title).all()
    user = getattr(request.state, "user", None)
    return templates.TemplateResponse(
        "topics/list.html",
        {
            "request": request,
            "topics": topics,
            "csrf_token": get_csrf_token(request),
            "user": user,
        },
    )

@router.post("/create", response_class=RedirectResponse, response_model=None)
async def topic_create(
    request: Request,
    current_user: Annotated[Union[User, RedirectResponse], Depends(require_admin_or_moderator)],
    db: Annotated[Session, Depends(get_db)],
    title: str = Form(""),
    csrf_token: str = Form(""),
):
    """Create a new topic in the bank."""
    if isinstance(current_user, RedirectResponse):
        return current_user
    validate_csrf(request, csrf_token)
    title = (title or "").strip()
    if not title:
        request.session.setdefault("flash", []).append(("danger", "Название темы обязательно."))
        return RedirectResponse(url="/topics", status_code=303)
    
    topic = Topic(title=title)
    db.add(topic)
    db.commit()
    db.refresh(topic)
    request.session.setdefault("flash", []).append(("success", "Тема добавлена."))
    return RedirectResponse(url="/topics", status_code=303)


@router.get("/{topic_id:int}/edit", response_class=HTMLResponse, response_model=None)
async def topic_edit(
    request: Request,
    topic_id: int,
    current_user: Annotated[Union[User, RedirectResponse], Depends(require_admin_or_moderator)],
    db: Annotated[Session, Depends(get_db)],
):
    """Edit topic title and manage its tasks."""
    if isinstance(current_user, RedirectResponse):
        return current_user
    topic = db.query(Topic).options(selectinload(Topic.tasks)).filter(Topic.id == topic_id).first()
    if not topic:
        raise HTTPException(status_code=404, detail="Тема не найдена")
    
    tasks = sorted(topic.tasks, key=lambda t: t.points)
    user = getattr(request.state, "user", None)
    return templates.TemplateResponse(
        "topics/edit.html",
        {
            "request": request,
            "topic": topic,
            "tasks": tasks,
            "csrf_token": get_csrf_token(request),
            "user": user,
        },
    )

@router.post("/{topic_id:int}/edit", response_class=RedirectResponse, response_model=None)
async def topic_edit_submit(
    request: Request,
    topic_id: int,
    current_user: Annotated[User, Depends(require_admin_or_moderator)],
    db: Annotated[Session, Depends(get_db)],
    title: str = Form(""),
    csrf_token: str = Form(""),
):
    """Update topic title."""
    validate_csrf(request, csrf_token)
    topic = db.query(Topic).filter(Topic.id == topic_id).first()
    if not topic:
        raise HTTPException(status_code=404, detail="Тема не найдена")
    title = (title or "").strip()
    if title:
        topic.title = title
        db.commit()
        request.session.setdefault("flash", []).append(("success", "Название обновлено."))
    return RedirectResponse(url=f"/topics/{topic_id}/edit", status_code=303)

@router.post("/{topic_id:int}/delete", response_class=RedirectResponse, response_model=None)
async def topic_delete(
    request: Request,
    topic_id: int,
    current_user: Annotated[Union[User, RedirectResponse], Depends(require_admin_or_moderator)],
    db: Annotated[Session, Depends(get_db)],
    csrf_token: str = Form(""),
):
    """Delete a topic from the bank."""
    if isinstance(current_user, RedirectResponse):
        return current_user
    validate_csrf(request, csrf_token)
    topic = db.query(Topic).filter(Topic.id == topic_id).first()
    if not topic:
        raise HTTPException(status_code=404, detail="Тема не найдена")

    # Check for usage in any games (via GameTopic)
    is_used = db.query(GameTopic).filter(GameTopic.topic_id == topic_id).first()
    
    # Check for usage of any of its tasks (via GameTask -> Task)
    task_used = db.query(GameTask).join(Task, GameTask.task_id == Task.id).filter(Task.topic_id == topic_id).first()

    if is_used or task_used:
        request.session.setdefault("flash", []).append(("danger", "Невозможно удалить тему: она или её задания привязаны к активным играм."))
        return RedirectResponse(url="/topics", status_code=303)

    db.delete(topic)
    db.commit()
    request.session.setdefault("flash", []).append(("success", "Тема успешно удалена из банка."))
    return RedirectResponse(url="/topics", status_code=303)

@router.post("/{topic_id:int}/tasks/create", response_class=RedirectResponse, response_model=None)
async def task_create(
    request: Request,
    topic_id: int,
    current_user: Annotated[Union[User, RedirectResponse], Depends(require_admin_or_moderator)],
    db: Annotated[Session, Depends(get_db)],
    text: str = Form(""),
    points: int = Form(10),
    correct_answer: str = Form(""),
    csrf_token: str = Form(""),
):
    """Add a task to a topic."""
    if isinstance(current_user, RedirectResponse):
        return current_user
    validate_csrf(request, csrf_token)
    topic = db.query(Topic).filter(Topic.id == topic_id).first()
    if not topic:
        raise HTTPException(status_code=404, detail="Тема не найдена")
    text = (text or "").strip()
    correct_answer = (correct_answer or "").strip()
    if not text or not correct_answer:
        request.session.setdefault("flash", []).append(("danger", "Текст и ответ обязательны."))
        return RedirectResponse(url=f"/topics/{topic_id}/edit", status_code=303)
    
    task = Task(topic_id=topic_id, text=text, points=points, correct_answer=correct_answer)
    db.add(task)
    db.commit()
    request.session.setdefault("flash", []).append(("success", "Задание добавлено."))
    return RedirectResponse(url=f"/topics/{topic_id}/edit", status_code=303)

@router.post("/{topic_id:int}/tasks/{task_id:int}/edit", response_class=RedirectResponse, response_model=None)
async def task_edit(
    request: Request,
    topic_id: int,
    task_id: int,
    current_user: Annotated[Union[User, RedirectResponse], Depends(require_admin_or_moderator)],
    db: Annotated[Session, Depends(get_db)],
    text: str = Form(""),
    points: int = Form(10),
    correct_answer: str = Form(""),
    csrf_token: str = Form(""),
):
    """Edit a task."""
    if isinstance(current_user, RedirectResponse):
        return current_user
    validate_csrf(request, csrf_token)
    task = db.query(Task).filter(Task.id == task_id, Task.topic_id == topic_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Задание не найдено")
    
    task.text = (text or "").strip()
    task.points = points
    task.correct_answer = (correct_answer or "").strip()
    db.commit()
    request.session.setdefault("flash", []).append(("success", "Задание обновлено."))
    return RedirectResponse(url=f"/topics/{topic_id}/edit", status_code=303)

@router.post("/{topic_id:int}/tasks/{task_id:int}/delete", response_class=RedirectResponse, response_model=None)
async def task_delete(
    request: Request,
    topic_id: int,
    task_id: int,
    current_user: Annotated[Union[User, RedirectResponse], Depends(require_admin_or_moderator)],
    db: Annotated[Session, Depends(get_db)],
    csrf_token: str = Form(""),
):
    """Delete a task."""
    if isinstance(current_user, RedirectResponse):
        return current_user
    validate_csrf(request, csrf_token)
    task = db.query(Task).filter(Task.id == task_id, Task.topic_id == topic_id).first()
    if task:
        # Check for usage in any games
        is_used = db.query(GameTask).filter(GameTask.task_id == task_id).first()
        if is_used:
            request.session.setdefault("flash", []).append(("danger", "Невозможно удалить задание: оно используется в активных играх."))
            return RedirectResponse(url=f"/topics/{topic_id}/edit", status_code=303)

        db.delete(task)
        db.commit()
        request.session.setdefault("flash", []).append(("success", "Задание удалено."))
    return RedirectResponse(url=f"/topics/{topic_id}/edit", status_code=303)
