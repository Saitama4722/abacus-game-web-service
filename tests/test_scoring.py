"""
Stage 10.3: Scoring logic verification (unit-style tests via service layer).

Base points 10,20,...,60; horizontal bonus 50/100; vertical bonus by column; superbonus for first N.
"""

import pytest
from sqlalchemy.orm import Session

from app.database import SessionLocal, init_db
from app.models import Answer, Game, GameTeam, Result, Task, Team, Topic, User
from app.services import game_service


@pytest.fixture(scope="module")
def db_session() -> Session:
    """Ensure DB tables exist and yield session. Uses same in-memory DB as conftest."""
    init_db()
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def fresh_db(db_session: Session) -> Session:
    """Clear data and ensure admin + one game with 6 topics × 6 tasks and one team."""
    for m in [Answer, Result, GameTeam, Task, Topic, Game, Team]:
        try:
            db_session.query(m).delete()
        except Exception:
            pass
    db_session.commit()
    # Default admin
    from app.models import User
    if db_session.query(User).filter(User.username == "admin").first() is None:
        import bcrypt
        u = User(username="admin", password_hash=bcrypt.hashpw(b"admin", bcrypt.gensalt()).decode("utf-8"), role="admin")
        db_session.add(u)
        db_session.commit()
    # One game, 6 topics, 6 tasks each; one team assigned
    game = Game(name="Score Test", status="in_progress", superbonus_winners_count=1)
    db_session.add(game)
    db_session.commit()
    db_session.refresh(game)
    team = Team(name="Team A")
    db_session.add(team)
    db_session.commit()
    db_session.refresh(team)
    db_session.add(GameTeam(game_id=game.id, team_id=team.id))
    for ti in range(1, 7):
        topic = Topic(game_id=game.id, title=f"Topic {ti}", order_index=ti)
        db_session.add(topic)
    db_session.commit()
    topics = db_session.query(Topic).filter(Topic.game_id == game.id).order_by(Topic.order_index).all()
    for topic in topics:
        for oi in range(1, 7):
            pts = 10 * oi
            task = Task(
                topic_id=topic.id,
                text=f"Q {topic.order_index}.{oi}",
                order_index=oi,
                points=pts,
                correct_answer=f"a{topic.order_index}_{oi}",
            )
            db_session.add(task)
    db_session.commit()
    return db_session


def test_base_points_10_20_30(fresh_db: Session) -> None:
    """Solve task 1 in topic 1 (10), task 2 in topic 1 (20), task 1 in topic 2 (10) -> base 40."""
    game = fresh_db.query(Game).first()
    team = fresh_db.query(Team).first()
    topics = fresh_db.query(Topic).filter(Topic.game_id == game.id).order_by(Topic.order_index).all()
    t1_task1 = next(t for t in topics[0].tasks if t.order_index == 1)
    t1_task2 = next(t for t in topics[0].tasks if t.order_index == 2)
    t2_task1 = next(t for t in topics[1].tasks if t.order_index == 1)
    for task, answer in [(t1_task1, "a1_1"), (t1_task2, "a1_2"), (t2_task1, "a2_1")]:
        ok, msg, correct = game_service.submit_answer(fresh_db, game.id, team.id, task.id, answer)
        assert ok and correct, msg
    result = fresh_db.query(Result).filter(Result.game_id == game.id, Result.team_id == team.id).first()
    assert result is not None
    assert result.score_base == 40


def test_horizontal_bonus_50_after_full_topic(fresh_db: Session) -> None:
    """Complete all 6 tasks in topic 1 -> horizontal bonus +50 (or +100 if first)."""
    game = fresh_db.query(Game).first()
    team = fresh_db.query(Team).first()
    topics = fresh_db.query(Topic).filter(Topic.game_id == game.id).order_by(Topic.order_index).all()
    topic1_tasks = sorted(topics[0].tasks, key=lambda t: t.order_index)
    for task in topic1_tasks:
        ans = f"a{topics[0].order_index}_{task.order_index}"
        ok, _, correct = game_service.submit_answer(fresh_db, game.id, team.id, task.id, ans)
        assert ok and correct
    fresh_db.expire_all()  # force reload
    result = fresh_db.query(Result).filter(Result.game_id == game.id, Result.team_id == team.id).first()
    assert result is not None
    # First (and only) team gets superbonus 100 for horizontal
    assert result.score_horizontal_bonus == 100
    assert result.score_base == sum(10 * i for i in range(1, 7))  # 210


def test_vertical_bonus_column1(fresh_db: Session) -> None:
    """Complete task 1 in all 6 topics -> vertical bonus for column 1 = 10 (or 20 if first)."""
    game = fresh_db.query(Game).first()
    team = fresh_db.query(Team).first()
    topics = fresh_db.query(Topic).filter(Topic.game_id == game.id).order_by(Topic.order_index).all()
    for topic in topics:
        task1 = next(t for t in topic.tasks if t.order_index == 1)
        ans = f"a{topic.order_index}_1"
        ok, _, correct = game_service.submit_answer(fresh_db, game.id, team.id, task1.id, ans)
        assert ok and correct
    fresh_db.expire_all()
    result = fresh_db.query(Result).filter(Result.game_id == game.id, Result.team_id == team.id).first()
    assert result is not None
    # Column 1 bonus = 10 points; first team gets double = 20
    assert result.score_vertical_bonus == 20
    assert result.score_base == 60  # 10*6


def test_duplicate_answer_rejected(fresh_db: Session) -> None:
    """Submitting answer for same task again returns success=False with message."""
    game = fresh_db.query(Game).first()
    team = fresh_db.query(Team).first()
    topic = fresh_db.query(Topic).filter(Topic.game_id == game.id).order_by(Topic.order_index).first()
    task = next(t for t in topic.tasks if t.order_index == 1)
    ok1, _, _ = game_service.submit_answer(fresh_db, game.id, team.id, task.id, "a1_1")
    assert ok1
    ok2, msg, _ = game_service.submit_answer(fresh_db, game.id, team.id, task.id, "a1_1")
    assert not ok2
    assert "отвечали" in msg or "уже" in msg.lower()


def test_finished_game_rejects_answer(fresh_db: Session) -> None:
    """When game status is finished, submit_answer returns failure."""
    game = fresh_db.query(Game).first()
    team = fresh_db.query(Team).first()
    topic = fresh_db.query(Topic).filter(Topic.game_id == game.id).order_by(Topic.order_index).first()
    task = next(t for t in topic.tasks if t.order_index == 1)
    game.status = "finished"
    fresh_db.commit()
    ok, msg, _ = game_service.submit_answer(fresh_db, game.id, team.id, task.id, "a1_1")
    assert not ok
    assert "завершена" in msg or "finished" in msg.lower()
