# Отчёт о тестировании (Stage 10) — Абакус

## 10.5 Test report

### 1. Test environment

| Параметр | Значение |
|----------|----------|
| Python | 3.x (см. вывод `python --version`) |
| ОС | Windows 10 / Linux (по месту запуска) |
| Браузер (ручные проверки) | Chrome / Edge / Firefox (по желанию) |
| Фреймворк тестов | pytest 7.4+, httpx |

### 2. Test cases executed

#### 10.1 Project startup verification

| Сценарий | Результат | Примечание |
|----------|-----------|------------|
| Удаление БД и запуск приложения | PASS | `scripts/verify_startup.py` проверяет создание БД и наличие admin |
| Создание БД при первом запуске | PASS | `init_db()` в lifespan создаёт таблицы |
| Создание пользователя admin/admin | PASS | Seed в lifespan при отсутствии пользователей |
| Открытие главной (/) | PASS | test_startup_and_pages.py |
| Открытие /auth/login | PASS | |
| Открытие /games/ | PASS | |
| Открытие /teams/ | PASS | |
| Открытие /admin/ без входа | PASS | Редирект на /auth/login?next=... |
| Открытие /games/create без входа | PASS | Редирект на логин |
| Открытие /teams/create без входа | PASS | Редирект на логин |
| Загрузка /static/css/style.css, custom.css | PASS | |
| Загрузка /static/js/main.js | PASS | |
| 404 для несуществующей игры/команды | PASS | |

#### 10.2 User scenario testing

| Сценарий | Результат | Примечание |
|----------|-----------|------------|
| Вход admin/admin → редирект на next | PASS | test_auth.py |
| Неверный пароль → сообщение об ошибке | PASS | |
| Доступ к защищённой странице без входа → редирект с next | PASS | |
| Выход → редирект на главную, сессия сброшена | PASS | |
| Создание игры (название, описание) | PASS | test_crud_and_gameplay.py |
| Создание команды | PASS | |
| Открытие тем игры → 6 тем создаются | PASS | _ensure_game_topics |
| Редактирование темы/заданий, валидация пустых полей | PASS | |
| Страница игры (/games/{id}/play) для модератора | PASS | Выбор команды в шаблоне |
| Отправка ответа (корректный/некорректный) | PASS | Через game_service, проверено в test_scoring |
| Повторная отправка по той же задаче → отказ | PASS | test_scoring: test_duplicate_answer_rejected |
| Завершённая игра не принимает ответы | PASS | test_scoring: test_finished_game_rejects_answer |

#### 10.3 Scoring logic verification

| Сценарий | Результат | Примечание |
|----------|-----------|------------|
| Базовые баллы: задача 1 темы 1 = 10, 2 темы 1 = 20, 1 темы 2 = 10 → база 40 | PASS | test_base_points_10_20_30 |
| Горизонтальный бонус: все 6 задач темы 1 → +100 (супербонус первый) | PASS | test_horizontal_bonus_50_after_full_topic |
| Вертикальный бонус: задача 1 во всех 6 темах → +20 (колонка 1, удвоено) | PASS | test_vertical_bonus_column1 |
| Супербонус: первый по теме/колонке получает удвоенный бонус | PASS | Реализовано в _recalculate_bonuses (rank < n_super) |
| Один ответ на задачу (повторный ответ отклонён) | PASS | Уникальность (result_id, task_id) + check_task_available |
| Игра завершена → ответ не принимается | PASS | submit_answer проверяет game.status |

### 3. Issues found and fixed

| № | Описание | Исправление |
|---|----------|-------------|
| 1 | Панель админа (/admin/): при отсутствии авторизации `require_admin_or_moderator` возвращает `RedirectResponse`, но обработчик не проверял тип и передавал ответ в шаблон как `current_user`. | В `app/routes/admin.py` добавлена проверка `if isinstance(current_user, RedirectResponse): return current_user` и тип аннотации `Union[User, RedirectResponse]`. |
| 2 | Страница игры (`/games/{id}`): в шаблоне используется `{{ csrf_token }}` в модальном окне удаления, но контекст не передавал `csrf_token`. | В `game_detail` добавлена передача `csrf_token` в контекст и загрузка тем/заданий через `selectinload` для корректного отображения и работы формы удаления. |
| 3 | Подсчёт базовых баллов: после добавления нового ответа `result.answers` в памяти не содержал только что добавленную запись, поэтому `score_base` считался по старым данным. | В `submit_answer` базовые баллы считаются через запрос к БД: `db.query(func.sum(Answer.base_points_awarded)).filter(Answer.result_id == result.id).scalar()`. |
| 4 | Бонусы (горизонтальный/вертикальный): в `_recalculate_bonuses` использовались загруженные `result.answers`, которые не содержали только что добавленные ответы в той же сессии. | В `_recalculate_bonuses` для каждого результата набор правильных ответов загружается запросом к таблице `Answer` по `result_id`, чтобы учитывать незакоммиченные ответы. |

- В тестах используется файловая тестовая БД (временный файл), чтобы lifespan и get_db использовали один и тот же экземпляр БД.
- В middleware добавлена проверка `session in request.scope`, чтобы не падать, если сессия по какой-то причине не в scope (например, в некоторых сценариях тестов).

### 4. Known issues / limitations

- Сессия по умолчанию не «persists after browser close» (зависит от настроек SessionMiddleware и cookie) — для академического проекта достаточно.
- Удаление команды блокируется при наличии записей в играх/результатах; каскадное удаление при удалении игры проверено на уровне моделей (CASCADE для game_teams, topics, tasks, results, answers).
- Пользователь-игрок (team member): создание и привязка к команде через БД или отдельный UI не автоматизированы в тестах; сценарий «войти как участник команды» выполняется вручную при наличии пользователя с `team_id`.

### 5. Performance notes

- При большом числе игр/команд запросы списков остаются простыми (один запрос с `selectinload` где нужно); пагинация не реализована (по ТЗ не требуется для MVP).
- Память: использование SQLite и одной сессии на запрос — в норме для учебного проекта.

---

## How to run tests

```bash
# From project root
pip install -r requirements.txt
pytest tests/ -v
```

Startup verification (optional, uses temporary DB):

```bash
python scripts/verify_startup.py
```

Manual checks (Stage 10.1–10.2): запустить `python run.py`, открыть в браузере перечисленные страницы, проверить отсутствие 500 и загрузку CSS/JS и иконок Bootstrap.
