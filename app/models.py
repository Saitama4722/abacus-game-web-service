"""
SQLAlchemy ORM models for the Abacus game web service.

Schema (Stage 3): User, Team, Game, Topic, Task, Answer, Result, GameTeam.
Abacus game: 6 topics × 6 tasks per game; tasks solved in order within each topic;
fixed points 10–60; bonuses for full rows/columns.
"""

from datetime import datetime
from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class User(Base):
    """
    User entity: players, moderators, and admins.
    Roles: admin, moderator, player (or team).
    Optional team_id links user to a team for member count.
    """

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(256), nullable=False)
    email: Mapped[str | None] = mapped_column(String(256), nullable=True)
    role: Mapped[str] = mapped_column(String(32), nullable=False, default="player")  # admin | moderator | player
    team_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("teams.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)

    team: Mapped["Team | None"] = relationship("Team", back_populates="members", foreign_keys=[team_id])

    def __repr__(self) -> str:
        return f"<User(id={self.id}, username={self.username!r})>"


class Team(Base):
    """
    Team entity: groups that participate in games.
    """

    __tablename__ = "teams"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)

    members: Mapped[list["User"]] = relationship(
        "User",
        back_populates="team",
        foreign_keys="User.team_id",
        lazy="selectin",
    )
    games: Mapped[list["Game"]] = relationship(
        "Game",
        secondary="game_teams",
        back_populates="teams",
        lazy="selectin",
    )
    results: Mapped[list["Result"]] = relationship(
        "Result",
        back_populates="team",
        foreign_keys="Result.team_id",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<Team(id={self.id}, name={self.name!r})>"


class Game(Base):
    """
    Game entity: one Abacus game (6 topics × 6 tasks).
    status: in_progress (default) | finished. When finished, no new answers allowed.
    superbonus_winners_count: how many first teams get double bonus (horizontal/vertical).
    """

    __tablename__ = "games"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="in_progress")  # in_progress | finished
    superbonus_winners_count: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)

    topics: Mapped[list["Topic"]] = relationship(
        "Topic",
        back_populates="game",
        order_by="Topic.order_index",
        lazy="selectin",
        cascade="all, delete-orphan",
    )
    teams: Mapped[list["Team"]] = relationship(
        "Team",
        secondary="game_teams",
        back_populates="games",
        lazy="selectin",
    )
    results: Mapped[list["Result"]] = relationship(
        "Result",
        back_populates="game",
        foreign_keys="Result.game_id",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<Game(id={self.id}, name={self.name!r})>"


class GameTeam(Base):
    """
    Association table: many-to-many between Game and Team.
    """

    __tablename__ = "game_teams"

    game_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("games.id", ondelete="CASCADE"),
        primary_key=True,
    )
    team_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("teams.id", ondelete="CASCADE"),
        primary_key=True,
    )

    def __repr__(self) -> str:
        return f"<GameTeam(game_id={self.game_id}, team_id={self.team_id})>"


class Topic(Base):
    """
    Topic entity: one of 6 topics per game.
    """

    __tablename__ = "topics"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    game_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("games.id", ondelete="CASCADE"),
        nullable=False,
    )
    title: Mapped[str] = mapped_column(String(256), nullable=False)
    order_index: Mapped[int] = mapped_column(Integer, nullable=False)  # 1–6

    __table_args__ = (UniqueConstraint("game_id", "order_index", name="uq_topic_game_order"),)

    game: Mapped["Game"] = relationship("Game", back_populates="topics")
    tasks: Mapped[list["Task"]] = relationship(
        "Task",
        back_populates="topic",
        order_by="Task.order_index",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<Topic(id={self.id}, game_id={self.game_id}, title={self.title!r})>"


class Task(Base):
    """
    Task entity: one of 6 tasks per topic; points 10, 20, …, 60 by order_index.
    """

    __tablename__ = "tasks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    topic_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("topics.id", ondelete="CASCADE"),
        nullable=False,
    )
    text: Mapped[str] = mapped_column(Text, nullable=False)
    order_index: Mapped[int] = mapped_column(Integer, nullable=False)  # 1–6
    points: Mapped[int] = mapped_column(Integer, nullable=False)  # 10, 20, 30, 40, 50, 60
    correct_answer: Mapped[str] = mapped_column(String(256), nullable=False)

    __table_args__ = (UniqueConstraint("topic_id", "order_index", name="uq_task_topic_order"),)

    topic: Mapped["Topic"] = relationship("Topic", back_populates="tasks")
    answers: Mapped[list["Answer"]] = relationship(
        "Answer",
        back_populates="task",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<Task(id={self.id}, topic_id={self.topic_id}, order_index={self.order_index})>"


class Result(Base):
    """
    Result entity: one game session per team per game.
    score_base: sum of base points from correct answers.
    score_horizontal_bonus / score_vertical_bonus: earned bonuses.
    superbonus_multiplier: 1.0 or 2.0 (first N teams get double).
    total_score: final score = (base + horizontal + vertical) * superbonus_multiplier.
    """

    __tablename__ = "results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    game_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("games.id", ondelete="CASCADE"),
        nullable=False,
    )
    team_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("teams.id", ondelete="CASCADE"),
        nullable=False,
    )
    started_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    score_base: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    score_horizontal_bonus: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    score_vertical_bonus: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    superbonus_multiplier: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    total_score: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    __table_args__ = (UniqueConstraint("game_id", "team_id", name="uq_result_game_team"),)

    game: Mapped["Game"] = relationship("Game", back_populates="results")
    team: Mapped["Team"] = relationship("Team", back_populates="results")
    answers: Mapped[list["Answer"]] = relationship(
        "Answer",
        back_populates="result",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<Result(id={self.id}, game_id={self.game_id}, team_id={self.team_id})>"


class Answer(Base):
    """
    Answer entity: one submission per task per result (given_answer, is_correct, base_points_awarded).
    """

    __tablename__ = "answers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    result_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("results.id", ondelete="CASCADE"),
        nullable=False,
    )
    task_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("tasks.id", ondelete="CASCADE"),
        nullable=False,
    )
    given_answer: Mapped[str] = mapped_column(Text, nullable=False)
    is_correct: Mapped[bool] = mapped_column(Boolean, nullable=False)
    base_points_awarded: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    answered_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)

    __table_args__ = (UniqueConstraint("result_id", "task_id", name="uq_answer_result_task"),)

    result: Mapped["Result"] = relationship("Result", back_populates="answers")
    task: Mapped["Task"] = relationship("Task", back_populates="answers")

    def __repr__(self) -> str:
        return f"<Answer(id={self.id}, result_id={self.result_id}, task_id={self.task_id})>"
