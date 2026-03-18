"""
Game logic service for Abaca: board state, task availability, answer submission,
bonus calculation (horizontal/vertical/superbonus), and game finish.

Rules: 6 topics × 6 tasks; tasks in a topic must be solved in order (1→6);
base points 10–60; horizontal bonus +50 (+100 for first N); vertical bonus +task_points (+double for first N).
"""

import logging
from datetime import datetime
from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session, selectinload

from app.models import Answer, Game, GameTeam, Result, Task, Team, Topic

logger = logging.getLogger(__name__)

NUM_TOPICS = 6
NUM_TASKS_PER_TOPIC = 6
HORIZONTAL_BONUS = 50
HORIZONTAL_SUPERBONUS = 100


def _get_or_create_result(db: Session, game_id: int, team_id: int) -> Result:
    """Get existing Result for (game_id, team_id) or create one."""
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


def get_game_board_state(
    db: Session,
    game_id: int,
    team_id: int | None = None,
) -> dict[str, Any]:
    """
    Build board state for play view: game, topics with tasks, per-team scores,
    and for viewing_team_id (if given) the status of each cell: available | solved | locked.

    Returns dict: game, topics (each with tasks and for each task: status for team_id, points),
    team_scores (list of {team_id, team_name, total_score}), viewing_team_id.
    """
    logger.debug("get_game_board_state: game_id=%s team_id=%s", game_id, team_id)
    game = (
        db.query(Game)
        .options(
            selectinload(Game.topics).selectinload(Topic.tasks),
            selectinload(Game.teams),
            selectinload(Game.results).selectinload(Result.answers),
        )
        .filter(Game.id == game_id)
        .first()
    )
    if game is None:
        logger.warning("get_game_board_state: game_id=%s not found", game_id)
        return {}

    topics = sorted(game.topics, key=lambda t: t.order_index)
    # Build task_id -> (topic_index 1-6, task order_index 1-6)
    task_id_to_topic_order: dict[int, int] = {}
    task_id_to_task_order: dict[int, int] = {}
    for topic in topics:
        for task in sorted(topic.tasks, key=lambda t: t.order_index):
            task_id_to_topic_order[task.id] = topic.order_index
            task_id_to_task_order[task.id] = task.order_index

    # Per-team: result and set of correct/answered task_ids. Initialize for ALL game teams
    # so that teams with no answers yet still get "available" for first task in each topic.
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

    # Sort by total_score desc for display
    team_scores.sort(key=lambda x: (-x["total_score"], x["team_name"]))

    # For each task cell: status for viewing team (any team in game, including those with no Result yet)
    cell_status: dict[tuple[int, int], str] = {}  # (topic_order, task_order) -> available|solved|locked
    if team_id is not None and team_id in game_team_ids:
        correct_set = team_correct.get(team_id, set())
        answered_set = team_answered.get(team_id, set())
        for topic in topics:
            to_idx = topic.order_index
            sorted_tasks = sorted(topic.tasks, key=lambda t: t.order_index)
            for task in sorted_tasks:
                tk_idx = task.order_index
                if task.id in answered_set:
                    cell_status[(to_idx, tk_idx)] = "solved" if task.id in correct_set else "attempted"
                else:
                    # Check if previous in topic are all solved
                    prev_ok = all(
                        any(t2.id in correct_set for t2 in sorted_tasks if t2.order_index == k)
                        for k in range(1, tk_idx)
                    )
                    cell_status[(to_idx, tk_idx)] = "available" if prev_ok else "locked"

    # Build topic rows for template: list of {topic, tasks: [{task, points, status}]}
    topic_rows = []
    for topic in topics:
        tasks_sorted = sorted(topic.tasks, key=lambda t: t.order_index)
        row = {
            "topic": topic,
            "tasks": [
                {
                    "task": t,
                    "points": t.points,
                    "status": cell_status.get((topic.order_index, t.order_index), "locked"),
                }
                for t in tasks_sorted
            ],
        }
        topic_rows.append(row)

    # Log board summary for debugging (e.g. why tasks are locked)
    if team_id is not None:
        available_count = sum(1 for r in topic_rows for c in r["tasks"] if c["status"] == "available")
        solved_count = sum(1 for r in topic_rows for c in r["tasks"] if c["status"] == "solved")
        locked_count = sum(1 for r in topic_rows for c in r["tasks"] if c["status"] == "locked")
        logger.info(
            "get_game_board_state: game_id=%s team_id=%s - Board summary: %s topics, %s cells (available=%s solved=%s locked=%s)",
            game_id, team_id, len(topics), sum(len(r["tasks"]) for r in topic_rows), available_count, solved_count, locked_count,
        )
    else:
        logger.debug("get_game_board_state: game_id=%s team_id=None - no cell status (scores only)", game_id)
    return {
        "game": game,
        "topics": topics,
        "topic_rows": topic_rows,
        "team_scores": team_scores,
        "viewing_team_id": team_id,
    }


def check_task_available(
    db: Session,
    game_id: int,
    team_id: int,
    task_id: int,
) -> tuple[bool, str]:
    """
    Check if the task can be opened for this team.
    Returns (True, "") if available, (False, message) otherwise.
    Rules: task must belong to game; team in game; previous tasks in same topic solved; one attempt.
    """
    logger.debug("check_task_available: game_id=%s team_id=%s task_id=%s", game_id, team_id, task_id)
    task = db.query(Task).filter(Task.id == task_id).first()
    if task is None:
        logger.debug("check_task_available: task_id=%s not found - LOCKED", task_id)
        return (False, "Задание не найдено")

    topic = db.query(Topic).filter(Topic.id == task.topic_id).first()
    if topic is None or topic.game_id != game_id:
        logger.debug("check_task_available: task_id=%s not in game - LOCKED", task_id)
        return (False, "Задание не принадлежит этой игре")

    in_game = (
        db.query(GameTeam).filter(GameTeam.game_id == game_id, GameTeam.team_id == team_id).first()
    )
    if not in_game:
        logger.debug("check_task_available: team_id=%s not in game - LOCKED", team_id)
        return (False, "Команда не участвует в этой игре")

    result = (
        db.query(Result).filter(Result.game_id == game_id, Result.team_id == team_id).first()
    )
    if result:
        answered = {a.task_id for a in result.answers}
        if task_id in answered:
            logger.debug("check_task_available: task_id=%s already answered - LOCKED", task_id)
            return (False, "Вы уже отвечали на эту задачу")

    # Same topic: all tasks with order_index < task.order_index must be correctly answered
    all_tasks_in_topic = (
        db.query(Task).filter(Task.topic_id == task.topic_id).order_by(Task.order_index).all()
    )
    if result:
        correct_ids = {a.task_id for a in result.answers if a.is_correct}
    else:
        correct_ids = set()
    for t in all_tasks_in_topic:
        if t.order_index < task.order_index and t.id not in correct_ids:
            logger.info(
                "check_task_available: task_id=%s (topic %s order %s) - previous task %s not solved - LOCKED",
                task_id, topic.order_index, task.order_index, t.id,
            )
            return (False, "Сначала решите предыдущие задачи в теме")

    logger.debug("check_task_available: task_id=%s - AVAILABLE", task_id)
    return (True, "")


def _recalculate_bonuses(db: Session, game_id: int) -> None:
    """
    Recompute horizontal and vertical bonuses for all teams in the game.
    Horizontal: all 6 tasks in a topic solved -> +50, or +100 for first superbonus_winners_count teams (by completion time).
    Vertical: same task number (1-6) in all 6 topics solved -> +task.points, or double for first N teams.
    """
    game = (
        db.query(Game)
        .options(selectinload(Game.topics).selectinload(Topic.tasks), selectinload(Game.results).selectinload(Result.answers))
        .filter(Game.id == game_id)
        .first()
    )
    if game is None:
        return

    n_super = max(1, getattr(game, "superbonus_winners_count", 1))
    topics = sorted(game.topics, key=lambda t: t.order_index)
    topic_ids = [t.id for t in topics]

    # Load correct answers from DB so newly added (uncommitted) answers are visible
    result_correct: dict[int, dict[int, datetime]] = {}
    for result in game.results:
        result_correct[result.id] = {
            a.task_id: a.answered_at
            for a in db.query(Answer).filter(Answer.result_id == result.id, Answer.is_correct == True).all()
        }

    for result in game.results:
        correct_by_task = result_correct.get(result.id, {})
        task_id_to_points: dict[int, int] = {}
        task_id_to_topic: dict[int, int] = {}
        task_id_to_order: dict[int, int] = {}
        for topic in topics:
            for t in topic.tasks:
                task_id_to_points[t.id] = t.points
                task_id_to_topic[t.id] = topic.order_index
                task_id_to_order[t.id] = t.order_index

        # Horizontal: for each topic (1..6), did this team complete all 6? completion_time = max(answered_at of 6 tasks)
        topic_completion: list[tuple[int, datetime | None]] = []  # (team_result_id, time) per topic
        # We need per-team per-topic completion time for ordering
        team_topic_times: dict[int, dict[int, datetime]] = {}  # result_id -> topic_order -> time
        for res in game.results:
            team_topic_times[res.id] = {}
            correct = result_correct.get(res.id, {})
            for topic in topics:
                task_ids_topic = [t.id for t in sorted(topic.tasks, key=lambda x: x.order_index)]
                if all(tid in correct for tid in task_ids_topic):
                    t_max = max(correct[tid] for tid in task_ids_topic)
                    team_topic_times[res.id][topic.order_index] = t_max
        # For each topic: list of (result_id, completion_time) for teams that completed
        topic_first_completions: dict[int, list[tuple[int, datetime]]] = {}
        for topic in topics:
            order = topic.order_index
            completions = [
                (res.id, team_topic_times[res.id][order])
                for res in game.results
                if order in team_topic_times.get(res.id, {})
            ]
            completions.sort(key=lambda x: x[1])
            topic_first_completions[order] = completions

        score_h = 0
        for topic in topics:
            order = topic.order_index
            task_ids_topic = [t.id for t in sorted(topic.tasks, key=lambda x: x.order_index)]
            if not all(tid in correct_by_task for tid in task_ids_topic):
                continue
            completions = topic_first_completions.get(order, [])
            rank = next((i for i, (rid, _) in enumerate(completions) if rid == result.id), None)
            if rank is not None:
                bonus = HORIZONTAL_SUPERBONUS if rank < n_super else HORIZONTAL_BONUS
                score_h += bonus

        # Vertical: for each task number 1..6, did team solve that number in all 6 topics?
        # task_number -> list of (result_id, completion_time) for teams that completed column
        task_number = 6  # 1..6
        column_first_completions: dict[int, list[tuple[int, datetime]]] = {}
        for col in range(1, task_number + 1):
            completions = []
            for res in game.results:
                correct = result_correct.get(res.id, {})
                # All topics must have task with order_index == col solved
                done = True
                t_max = None
                for topic in topics:
                    task_in_col = next(
                        (t for t in topic.tasks if t.order_index == col),
                        None,
                    )
                    if task_in_col is None or task_in_col.id not in correct:
                        done = False
                        break
                    if t_max is None or correct[task_in_col.id] > t_max:
                        t_max = correct[task_in_col.id]
                if done and t_max is not None:
                    completions.append((res.id, t_max))
            completions.sort(key=lambda x: x[1])
            column_first_completions[col] = completions

        score_v = 0
        for col in range(1, 7):
            # Points for this column = points of any task in that column (e.g. 10,20,...,60)
            pts = 10 * col
            # Check if result has all 6 topics solved for this column
            solved = True
            for topic in topics:
                t = next((x for x in topic.tasks if x.order_index == col), None)
                if t is None or t.id not in correct_by_task:
                    solved = False
                    break
            if not solved:
                continue
            completions = column_first_completions.get(col, [])
            rank = next((i for i, (rid, _) in enumerate(completions) if rid == result.id), None)
            if rank is not None:
                bonus_pts = 2 * pts if rank < n_super else pts
                score_v += bonus_pts

        result.score_horizontal_bonus = score_h
        result.score_vertical_bonus = score_v
        result.total_score = (
            result.score_base + result.score_horizontal_bonus + result.score_vertical_bonus
        )
        logger.debug(
            "_recalculate_bonuses: game_id=%s result_id=%s team_id=%s - base=%s H_bonus=%s V_bonus=%s total=%s",
            game_id, result.id, result.team_id, result.score_base, score_h, score_v, result.total_score,
        )

    db.commit()
    logger.debug("_recalculate_bonuses: game_id=%s - committed", game_id)


def submit_answer(
    db: Session,
    game_id: int,
    team_id: int,
    task_id: int,
    submitted_answer: str,
) -> tuple[bool, str, bool]:
    """
    Submit an answer for the task. Validates order and one attempt; creates Answer; updates Result and bonuses.
    Returns (success, message, is_correct). success=False means validation failed (no Answer created).
    """
    game = db.query(Game).filter(Game.id == game_id).first()
    if game is None:
        return (False, "Игра не найдена", False)
    if getattr(game, "status", "in_progress") == "finished":
        return (False, "Игра завершена. Ответы больше не принимаются.", False)

    ok, msg = check_task_available(db, game_id, team_id, task_id)
    if not ok:
        return (False, msg, False)

    task = db.query(Task).filter(Task.id == task_id).first()
    if task is None:
        return (False, "Задание не найдено", False)

    result = _get_or_create_result(db, game_id, team_id)
    correct = (task.correct_answer or "").strip().lower() == (submitted_answer or "").strip().lower()
    points = task.points if correct else 0
    logger.info(
        "submit_answer: game_id=%s team_id=%s task_id=%s - correct=%s points=%s (answer comparison)",
        game_id, team_id, task_id, correct, points,
    )

    answer = Answer(
        result_id=result.id,
        task_id=task_id,
        given_answer=(submitted_answer or "").strip(),
        is_correct=correct,
        base_points_awarded=points,
    )
    db.add(answer)
    db.flush()

    # Recompute base from DB so the new answer is included (result.answers collection may not be updated yet in this session)
    result.score_base = int(
        db.query(func.coalesce(func.sum(Answer.base_points_awarded), 0))
        .filter(Answer.result_id == result.id)
        .scalar()
        or 0
    )
    _recalculate_bonuses(db, game_id)
    db.refresh(result)

    logger.info(
        "submit_answer: game_id=%s team_id=%s task_id=%s - Result: success correct=%s points_awarded=%s",
        game_id, team_id, task_id, correct, points,
    )
    return (True, "Ответ принят. Правильно!" if correct else "Ответ принят. Неправильно.", correct)


def calculate_scores(db: Session, game_id: int, team_id: int) -> dict[str, Any]:
    """Return current score breakdown for a team in the game."""
    result = (
        db.query(Result)
        .filter(Result.game_id == game_id, Result.team_id == team_id)
        .first()
    )
    if result is None:
        return {
            "score_base": 0,
            "score_horizontal_bonus": 0,
            "score_vertical_bonus": 0,
            "superbonus_multiplier": 1.0,
            "total_score": 0,
        }
    return {
        "score_base": result.score_base,
        "score_horizontal_bonus": result.score_horizontal_bonus,
        "score_vertical_bonus": result.score_vertical_bonus,
        "superbonus_multiplier": getattr(result, "superbonus_multiplier", 1.0),
        "total_score": result.total_score,
    }


def finish_game(db: Session, game_id: int) -> bool:
    """Set game status to finished. Returns True on success."""
    game = db.query(Game).filter(Game.id == game_id).first()
    if game is None:
        return False
    game.status = "finished"
    db.commit()
    logger.info("Game finished: game_id=%s", game_id)
    return True
