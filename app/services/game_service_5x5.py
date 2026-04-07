import logging
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session, selectinload

from app.models import Answer, Game, GameTeam, GameTopic, GameTask, Result, Task, Team, Topic

logger = logging.getLogger(__name__)

NUM_TOPICS = 5
NUM_TASKS_PER_TOPIC = 5

BONUS_LINE = 50


def is_game_paused(game: Game) -> bool:
    """Check if game is currently paused."""
    return getattr(game, "status", "in_progress") == "paused"


def is_game_time_expired(game: Game) -> bool:
    start = getattr(game, "start_time", None)
    duration = getattr(game, "duration_minutes", None)
    if start is None or duration is None:
        return False
    if is_game_paused(game):
        return False
    end_time = start + timedelta(minutes=duration)
    return datetime.utcnow() > end_time


def get_game_end_time(game: Game) -> datetime | None:
    start = getattr(game, "start_time", None)
    duration = getattr(game, "duration_minutes", None)
    if start is None or duration is None:
        return None
    return start + timedelta(minutes=duration)


def _get_or_create_result(db: Session, game_id: int, team_id: int) -> Result:
    result = (
        db.query(Result)
        .filter(Result.game_id == game_id, Result.team_id == team_id)
        .first()
    )
    if result is None:
        result = Result(game_id=game_id, team_id=team_id)
        db.add(result)
        db.commit()
        db.refresh(result)
    return result


def get_game_board_state_5x5(
    db: Session,
    game_id: int,
    team_id: int | None = None,
) -> dict[str, Any]:
    """
    Build board state for 5x5: game, 5 topics with 5 tasks, per-team scores.
    """
    game = (
        db.query(Game)
        .options(
            selectinload(Game.game_topics).selectinload(GameTopic.topic),
            selectinload(Game.game_topics).selectinload(GameTopic.game_tasks).selectinload(GameTask.task),
            selectinload(Game.teams),
            selectinload(Game.results).selectinload(Result.answers),
        )
        .filter(Game.id == game_id)
        .first()
    )
    if game is None:
        return {}

    g_topics = sorted(game.game_topics, key=lambda t: t.order_index)

    game_team_ids = {t.id for t in game.teams}
    team_correct: dict[int, set[int]] = {tid: set() for tid in game_team_ids}
    team_answered: dict[int, set[int]] = {tid: set() for tid in game_team_ids}
    team_result: dict[int, Result] = {}
    for result in game.results:
        tid = result.team_id
        team_result[tid] = result
        team_correct[tid] = {a.task_id for a in result.answers if a.is_correct}
        team_answered[tid] = {a.task_id for a in result.answers}

    team_scores = []
    for team in game.teams:
        res = team_result.get(team.id)
        total = res.total_score if res else 0
        team_scores.append({"team_id": team.id, "team_name": team.name, "total_score": total})

    team_scores.sort(key=lambda x: (-x["total_score"], x["team_name"]))

    cell_status: dict[tuple[int, int], str] = {}
    if team_id is not None and team_id in game_team_ids:
        correct_set = team_correct.get(team_id, set())
        answered_set = team_answered.get(team_id, set())
        for gt in g_topics:
            to_idx = gt.order_index
            sorted_tasks = sorted(gt.game_tasks, key=lambda t: t.order_index)
            for gtask in sorted_tasks:
                tk_idx = gtask.order_index
                task = gtask.task
                if task.id in answered_set:
                    cell_status[(to_idx, tk_idx)] = "solved" if task.id in correct_set else "attempted"
                else:
                    # In 5x5 all unattempted tasks are available
                    cell_status[(to_idx, tk_idx)] = "available"

    topic_rows = []
    for t_idx in range(1, NUM_TOPICS + 1):
        gt = next((g for g in g_topics if g.order_index == t_idx), None)
        if gt is None:
            topic_rows.append({
                "order_index": t_idx,
                "topic": None,
                "tasks": [{"order_index": k, "task": None, "points": 0, "status": "empty"} for k in range(1, NUM_TASKS_PER_TOPIC + 1)]
            })
            continue

        tasks_sorted = sorted(gt.game_tasks, key=lambda t: t.order_index)
        row_tasks = []
        for k in range(1, NUM_TASKS_PER_TOPIC + 1):
            gtask = next((t for t in tasks_sorted if t.order_index == k), None)
            if gtask is None:
                row_tasks.append({"order_index": k, "task": None, "points": 0, "status": "empty"})
            else:
                row_tasks.append({
                    "order_index": k,
                    "task": gtask.task,
                    "points": gtask.task.points,
                    "status": cell_status.get((gt.order_index, gtask.order_index), "available")
                })
        row = {
            "order_index": gt.order_index,
            "topic": gt.topic,
            "tasks": row_tasks
        }
        topic_rows.append(row)

    return {
        "game": game,
        "topics": g_topics,
        "topic_rows": topic_rows,
        "team_scores": team_scores,
        "viewing_team_id": team_id,
    }


def check_task_available_5x5(
    db: Session,
    game_id: int,
    team_id: int,
    task_id: int,
) -> tuple[bool, str]:
    """Check if the task can be opened in 5x5."""
    game_task = (
        db.query(GameTask)
        .join(GameTopic)
        .filter(GameTopic.game_id == game_id, GameTask.task_id == task_id)
        .first()
    )
    if game_task is None:
        return (False, "Задание не принадлежит этой игре")

    in_game = (
        db.query(GameTeam).filter(GameTeam.game_id == game_id, GameTeam.team_id == team_id).first()
    )
    if not in_game:
        return (False, "Команда не участвует в этой игре")

    result = (
        db.query(Result).filter(Result.game_id == game_id, Result.team_id == team_id).first()
    )
    if result:
        answered_ids = {a.task_id for a in result.answers}
        if task_id in answered_ids:
            return (False, "Вы уже отвечали на эту задачу")

    # In 5x5, no order prerequisites.
    return (True, "")


def _recalculate_bonuses_5x5(db: Session, game_id: int) -> None:
    """Compute score and bonuses for 5x5. Horizontal=50, Vertical=50, Diagonals=50."""
    game = (
        db.query(Game)
        .options(
            selectinload(Game.game_topics).selectinload(GameTopic.game_tasks), 
            selectinload(Game.results).selectinload(Result.answers)
        )
        .filter(Game.id == game_id)
        .first()
    )
    if game is None:
        return

    g_topics = sorted(game.game_topics, key=lambda t: t.order_index)

    # We map board as matrix [1..5][1..5] to task_id
    board_matrix = {}
    for gt in g_topics:
        t_idx = gt.order_index
        for gtask in gt.game_tasks:
            board_matrix[(t_idx, gtask.order_index)] = gtask.task_id

    result_correct = {}
    for result in game.results:
        result_correct[result.id] = {
            a.task_id
            for a in db.query(Answer).filter(Answer.result_id == result.id, Answer.is_correct == True).all()
        }

    for result in game.results:
        correct_set = result_correct.get(result.id, set())

        lines_completed = 0

        # Horizontal
        for i in range(1, NUM_TOPICS + 1):
            is_line = True
            for j in range(1, NUM_TASKS_PER_TOPIC + 1):
                tid = board_matrix.get((i, j))
                if not tid or tid not in correct_set:
                    is_line = False
                    break
            if is_line:
                lines_completed += 1

        # Vertical
        for j in range(1, NUM_TASKS_PER_TOPIC + 1):
            is_line = True
            for i in range(1, NUM_TOPICS + 1):
                tid = board_matrix.get((i, j))
                if not tid or tid not in correct_set:
                    is_line = False
                    break
            if is_line:
                lines_completed += 1

        # Diagonal 1
        is_diag1 = True
        for i in range(1, NUM_TOPICS + 1):
            tid = board_matrix.get((i, i))
            if not tid or tid not in correct_set:
                is_diag1 = False
                break
        if is_diag1:
            lines_completed += 1

        # Diagonal 2
        is_diag2 = True
        for i in range(1, NUM_TOPICS + 1):
            j = NUM_TASKS_PER_TOPIC - i + 1
            tid = board_matrix.get((i, j))
            if not tid or tid not in correct_set:
                is_diag2 = False
                break
        if is_diag2:
            lines_completed += 1

        # Use score_horizontal_bonus to store all lines bonus for 5x5
        result.score_horizontal_bonus = lines_completed * BONUS_LINE
        result.score_vertical_bonus = 0

        # Base score is auto-summed inside submit_answer_5x5 or we can sum here just to be safe
        result.total_score = result.score_base + result.score_horizontal_bonus + result.score_vertical_bonus

    db.commit()


def submit_answer_5x5(
    db: Session,
    game_id: int,
    team_id: int,
    task_id: int,
    submitted_answer: str,
) -> tuple[bool, str, bool]:
    game = db.query(Game).filter(Game.id == game_id).first()
    if game is None:
        return (False, "Игра не найдена", False)
    if getattr(game, "status", "in_progress") == "finished":
        return (False, "Игра завершена. Ответы больше не принимаются.", False)
    if is_game_paused(game):
        return (False, "Игра приостановлена. Ответы временно не принимаются.", False)
    if is_game_time_expired(game):
        return (False, "Время игры истекло. Ответы больше не принимаются.", False)
    if getattr(game, "start_time", None) and datetime.utcnow() < game.start_time:
        return (False, "Игра ещё не началась.", False)

    ok, msg = check_task_available_5x5(db, game_id, team_id, task_id)
    if not ok:
        return (False, msg, False)

    task = db.query(Task).filter(Task.id == task_id).first()
    if task is None:
        return (False, "Задание не найдено", False)

    result = _get_or_create_result(db, game_id, team_id)
    correct = (task.correct_answer or "").strip().lower() == (submitted_answer or "").strip().lower()
    points = task.points if correct else 0

    answer = Answer(
        result_id=result.id,
        task_id=task_id,
        given_answer=(submitted_answer or "").strip(),
        is_correct=correct,
        base_points_awarded=points,
    )
    db.add(answer)
    db.flush()

    result.score_base = int(
        db.query(func.coalesce(func.sum(Answer.base_points_awarded), 0))
        .filter(Answer.result_id == result.id)
        .scalar()
        or 0
    )
    
    _recalculate_bonuses_5x5(db, game_id)
    db.refresh(result)

    return (True, "Ответ принят. Правильно!" if correct else "Ответ принят. Неправильно.", correct)
