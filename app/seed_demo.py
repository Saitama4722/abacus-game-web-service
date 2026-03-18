"""
Seed demo data for immediate gameplay.

Used by app lifespan (when no games exist) and by scripts/seed_demo_data.py.
"""

DEMO_GAME_TITLE = "Демо-игра Абакус"
POINTS = [10, 20, 30, 40, 50, 60]

TOPICS_DATA = [
    (
        "Арифметика",
        [
            ("2 + 2 = ?", "4"),
            ("15 × 3 = ?", "45"),
            ("144 ÷ 12 = ?", "12"),
            ("7² + 24 = ?", "73"),
            ("Квадратный корень из 169", "13"),
            ("25% от 480", "120"),
        ],
    ),
    (
        "Алгебра",
        [
            ("x + 5 = 12, x = ?", "7"),
            ("2x - 3 = 7, x = ?", "5"),
            ("x² = 81, x = ? (положительный)", "9"),
            ("3x + 4 = 19, x = ?", "5"),
            ("x/4 + 6 = 10, x = ?", "16"),
            ("2(x + 3) = 18, x = ?", "6"),
        ],
    ),
    (
        "Геометрия",
        [
            ("Сколько сторон у квадрата?", "4"),
            ("Площадь прямоугольника 5×3", "15"),
            ("Периметр квадрата со стороной 6", "24"),
            ("Гипотенуза треугольника 3-4-5", "5"),
            ("Углы в треугольнике: 30°, 60°, ?", "90"),
            ("Длина окружности радиус 7 (π≈3.14)", "43.96"),
        ],
    ),
    (
        "Комбинаторика",
        [
            ("Сколько двузначных чисел из цифр 1,2,3 без повтора?", "6"),
            ("5! = ?", "120"),
            ("C(5,2) = ?", "10"),
            ("Сколькими способами 3 человека встали в очередь?", "6"),
            ("C(6,3) = ?", "20"),
            ("Сколько подмножеств у множества из 4 элементов?", "16"),
        ],
    ),
    (
        "Логика",
        [
            ("Следующее: 2, 4, 6, 8, ?", "10"),
            ("Истина и Ложь = ? (логика)", "0"),
            ("Следующее: 1, 1, 2, 3, 5, ?", "8"),
            ("Не (A и не A) — это всегда?", "истина"),
            ("Сколько всего значений у одной булевой переменной?", "2"),
            ("Следующее в ряду: 1, 4, 9, 16, ?", "25"),
        ],
    ),
    (
        "Числовые последовательности",
        [
            ("Продолжить: 3, 6, 9, 12, ?", "15"),
            ("Продолжить: 1, 4, 7, 10, ?", "13"),
            ("Продолжить: 2, 4, 8, 16, ?", "32"),
            ("Продолжить: 1, 3, 6, 10, 15, ?", "21"),
            ("Продолжить: 1, 2, 4, 7, 11, ?", "16"),
            ("Продолжить: 5, 10, 20, 40, ?", "80"),
        ],
    ),
]


def seed_demo_data():
    """
    Create demo game with teams, topics, tasks if not already present.
    Returns (created: bool, message: str).
    """
    from app.database import SessionLocal, init_db
    from app.models import Game, GameTeam, Task, Team, Topic

    init_db()
    db = SessionLocal()
    try:
        existing = db.query(Game).filter(Game.name == DEMO_GAME_TITLE).first()
        if existing:
            return False, "Демо-игра уже существует."

        game = Game(
            name=DEMO_GAME_TITLE,
            description="Демонстрационная игра для быстрого старта.",
            is_active=True,
            status="in_progress",
        )
        db.add(game)
        db.flush()

        team_alpha = Team(name="Команда Альфа")
        team_beta = Team(name="Команда Бета")
        db.add(team_alpha)
        db.add(team_beta)
        db.flush()

        db.add(GameTeam(game_id=game.id, team_id=team_alpha.id))
        db.add(GameTeam(game_id=game.id, team_id=team_beta.id))

        for order_index, (title, tasks_list) in enumerate(TOPICS_DATA, start=1):
            topic = Topic(
                game_id=game.id,
                title=f"Тема {order_index}: {title}",
                order_index=order_index,
            )
            db.add(topic)
            db.flush()
            for idx, (text, correct_answer) in enumerate(tasks_list, start=1):
                task = Task(
                    topic_id=topic.id,
                    text=text,
                    order_index=idx,
                    points=POINTS[idx - 1],
                    correct_answer=correct_answer.strip(),
                )
                db.add(task)

        db.commit()

        summary = (
            f"Создано: игра «{DEMO_GAME_TITLE}», 2 команды, 6 тем, 36 заданий. "
            "Статус игры: активна."
        )
        return True, summary
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
