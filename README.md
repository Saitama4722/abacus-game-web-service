<!-- ==================== РУССКАЯ ВЕРСИЯ ==================== -->

# 🧮 Абакус — веб-сервис для математических игр  
## Abacus Game Web Service

[![Python](https://img.shields.io/badge/Python-3.9+-3776AB?style=flat-square&logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.109+-009688?style=flat-square&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![SQLite](https://img.shields.io/badge/SQLite-3-003B57?style=flat-square&logo=sqlite&logoColor=white)](https://www.sqlite.org/)
[![License](https://img.shields.io/badge/License-Educational-blue?style=flat-square)](./README.md#-лицензия)
[![Last Commit](https://img.shields.io/github/last-commit/Saitama4722/abacus-game-web-service?style=flat-square)](https://github.com/Saitama4722/abacus-game-web-service)

---

## 📋 Описание

Веб-сервис для **создания и проведения математических игр** — учебный проект на Python и FastAPI. Реализованы две игры с различной механикой:

- **«Абакус» (6×6)** — классическая игра с последовательным решением заданий и бонусами за строки/столбцы
- **«Пять-на-пять» (5×5)** — стратегическая игра с фокусом на сборе линий (горизонтали, вертикали, диагонали)

Полный цикл: создание игр, управление командами, проведение турниров, автоматический подсчёт очков, система ролей, адаптивный интерфейс на русском языке.

---

## ✨ Возможности

### Игровая механика
- **Две игры с разной стратегией:**
  - **Абакус (6×6)** — последовательное решение заданий, бонусы за строки/столбцы
  - **Пять-на-пять (5×5)** — свободный выбор заданий, бонусы за линии (+50 за каждую)
- **Система очков** — базовые баллы за задания, бонусы за достижения, автоматический подсчёт
- **Строгая валидация** — проверка ответов, контроль доступности заданий

### Управление
- **CRUD игр и команд** — создание, редактирование, удаление
- **Редактор игрового поля** — настройка тем и заданий для каждой игры
- **Система ролей** — администратор, модератор, команда
- **Управление турниром** — пауза, возобновление, завершение игры

### Технические возможности
- **Адаптивный интерфейс** — Bootstrap 5, полностью на русском языке
- **Автоматическая демонстрация** — при первом запуске создаются демо-игры и учётная запись admin/admin
- **Автоматический выбор порта** — если порт 8000 занят, используется следующий доступный
- **Тестирование** — pytest для unit-тестов, Playwright для E2E browser-тестов

---

## 🛠 Технологии

| Компонент | Технология |
|-----------|------------|
| **Язык** | 🐍 Python 3.9+ |
| **Бэкенд** | ⚡ FastAPI |
| **БД** | 🗄️ SQLite + SQLAlchemy (ORM) |
| **Шаблоны** | 📄 Jinja2 |
| **Фронтенд** | 🎨 Bootstrap 5 |
| **Сервер** | 🚀 Uvicorn |

---

## 🚀 Быстрый старт

### Требования

- **Python 3.9+**

### Шаги

**1. Клонируйте репозиторий и перейдите в каталог:**

```bash
git clone https://github.com/Saitama4722/abacus-game-web-service.git
cd abacus-game-web-service
```

**2. Создайте виртуальное окружение и активируйте его.**

Windows (PowerShell):

```powershell
python -m venv venv
venv\Scripts\activate
```

Linux / macOS:

```bash
python3 -m venv venv
source venv/bin/activate
```

**3. Установите зависимости:**

```bash
pip install -r requirements.txt
```

**4. Запустите приложение:**

```bash
python run.py
```

Используется **автоматический выбор порта** (8000, 8001, … при занятости). В консоли будет выведен адрес вида **`http://127.0.0.1:[port]`** — откройте его в браузере.

**5. Первый запуск — демо-игра и учётная запись:**

- При **первом запуске** автоматически создаётся **демо-игра** и учётная запись администратора.
- **Логин по умолчанию:** `admin`
- **Пароль по умолчанию:** `admin`

Вход: главная страница → «Вход» → введите `admin` / `admin`. В production обязательно смените пароль.

---

## 🎮 Реализованные игры

### Абакус (6×6)
**Классическая игра с последовательным решением**

- **Поле:** 6 тем × 6 заданий
- **Правила:** задания в каждой теме решаются строго по порядку (1→2→3→4→5→6)
- **Баллы:** фиксированные (10, 20, 30, 40, 50, 60)
- **Бонусы:**
  - Горизонталь (полная тема): +50 баллов
  - Вертикаль (одинаковый номер задания во всех темах): +стоимость задания
  - Супербонус: первая команда получает удвоенные бонусы
- **Стратегия:** важен порядок решения и скорость

### Пять-на-пять (5×5)
**Стратегическая игра со сбором линий**

- **Поле:** 5 тем × 5 заданий
- **Правила:** все задания доступны сразу, можно выбирать любое
- **Баллы:** за каждое правильное задание
- **Бонусы:** +50 баллов за каждую собранную линию:
  - 5 горизонталей (полные строки)
  - 5 вертикалей (полные столбцы)
  - 2 диагонали (главная и побочная)
- **Максимум:** до 12 линий = до +600 бонусных баллов
- **Стратегия:** планирование, какие линии собирать первыми

### Как начать играть

1. Запустите `python run.py` и откройте адрес из консоли
2. Войдите: **admin** / **admin**
3. Перейдите в **«Игры»** → выберите демо-игру
4. Нажмите **«Играть»** → выберите команду
5. Решайте задания, следя за цветами ячеек:
   - 🟢 **Зелёная** — доступно
   - ✅ **Галочка** — решено верно
   - ❌ **Крестик** — решено неверно
   - 🔒 **Замок** — заблокировано (только для Абакуса)

---

## 👥 Роли пользователей

| Роль | Описание |
|------|----------|
| **Администратор (Admin)** | Полный доступ: создание и редактирование игр и команд, управление пользователями, проведение турниров. |
| **Модератор** | Проведение игр, проверка ответов, управление ходом турнира в рамках настроек администратора. |
| **Команда (Team)** | Участие в играх: просмотр заданий, отправка ответов, просмотр результатов. |

---

## 📁 Структура проекта

```
abacus-game-web-service/
├── app/
│   ├── __init__.py
│   ├── main.py          # FastAPI-приложение, статика, шаблоны
│   ├── config.py        # Настройки (DATABASE_URL, SECRET_KEY, PORT)
│   ├── database.py      # SQLAlchemy: engine, session, init_db
│   ├── deps.py          # Зависимости авторизации
│   ├── models.py        # ORM: User, Team, Game, Topic, Task, Answer, Result, GameTeam
│   ├── routes/          # Маршруты: auth, admin, games, teams
│   └── services/        # Бизнес-логика (game_service и др.)
├── templates/           # Jinja2 HTML (base, index, login, admin, games, teams)
├── static/              # CSS, JS
├── scripts/
│   └── seed_demo_data.py # Ручное создание демо-игры (опционально)
├── tests/               # Тесты (pytest)
├── run.py               # Запуск с авто-выбором порта
├── requirements.txt
├── README.md
├── DEMO.md              # Сценарий демонстрации
└── COURSEWORK.md        # Текстовые блоки для курсовой
```

---

## 🧪 Тестирование

### Unit-тесты (pytest)

```bash
pytest tests/ -v
```

Запускает unit-тесты: авторизация, CRUD-операции, игровая логика, система подсчёта очков.

### E2E browser-тесты (Playwright)

**Установка (один раз):**
```bash
npm install
npx playwright install
```

**Запуск тестов:**
```bash
npm test
```

Автоматические браузерные тесты проверяют:
- Доступность страниц
- Аутентификацию пользователей
- Создание игр (admin flow)
- Открытие и решение заданий
- Корректность рендеринга шаблонов

**Дополнительные команды:**
```bash
npm run test:headed    # С видимым браузером
npm run test:ui        # Интерактивный UI-режим
```

---

## 📄 Лицензия

Учебный проект для курсовой работы. Формальная лицензия не указана. Использование в образовательных целях приветствуется.

---

## � Контакты

- **GitHub:** [Saitama4722](https://github.com/Saitama4722)
- **Telegram:** [@VadikQA](https://t.me/VadikQA)
- **Репозиторий:** [github.com/Saitama4722/abacus-game-web-service](https://github.com/Saitama4722/abacus-game-web-service)

---

<!-- ==================== ENGLISH VERSION ==================== -->

# 🧮 Abacus — Web Service for Mathematical Games

[![Python](https://img.shields.io/badge/Python-3.9+-3776AB?style=flat-square&logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.109+-009688?style=flat-square&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![SQLite](https://img.shields.io/badge/SQLite-3-003B57?style=flat-square&logo=sqlite&logoColor=white)](https://www.sqlite.org/)
[![License](https://img.shields.io/badge/License-Educational-blue?style=flat-square)](./README.md#-license)
[![Last Commit](https://img.shields.io/github/last-commit/Saitama4722/abacus-game-web-service?style=flat-square)](https://github.com/Saitama4722/abacus-game-web-service)

---

## 📋 Description

**Web service for creating and conducting mathematical games** — educational Python project built with FastAPI. Two games with different mechanics:

- **«Abacus» (6×6)** — classic game with sequential task solving and row/column bonuses
- **«Five-by-Five» (5×5)** — strategic game focused on collecting lines (horizontal, vertical, diagonal)

Complete cycle: game creation, team management, tournament hosting, automatic scoring, role system, responsive Russian interface.

---

## ✨ Features

### Game Mechanics
- **Two games with different strategies:**
  - **Abacus (6×6)** — sequential task solving, row/column bonuses
  - **Five-by-Five (5×5)** — free task selection, line bonuses (+50 each)
- **Scoring system** — base points for tasks, achievement bonuses, automatic calculation
- **Strict validation** — answer checking, task availability control

### Management
- **Full CRUD** for games and teams — create, edit, delete
- **Game board editor** — configure topics and tasks per game
- **Role system** — administrator, moderator, team
- **Tournament control** — pause, resume, finish game

### Technical Features
- **Responsive UI** — Bootstrap 5, fully in Russian
- **Auto demo** — demo games and admin/admin account created on first launch
- **Auto port selection** — uses next available port if 8000 is busy
- **Testing** — pytest for unit tests, Playwright for E2E browser tests

---

## 🛠 Tech Stack

| Component | Technology |
|-----------|------------|
| **Language** | 🐍 Python 3.9+ |
| **Backend** | ⚡ FastAPI |
| **Database** | 🗄️ SQLite + SQLAlchemy (ORM) |
| **Templates** | 📄 Jinja2 |
| **Frontend** | 🎨 Bootstrap 5 |
| **Server** | 🚀 Uvicorn |

---

## 🚀 Quick Start

### Prerequisites

- **Python 3.9+**

### Steps

**1. Clone and enter the project directory:**

```bash
git clone https://github.com/Saitama4722/abacus-game-web-service.git
cd abacus-game-web-service
```

**2. Create and activate a virtual environment.**

Windows (PowerShell):

```powershell
python -m venv venv
venv\Scripts\activate
```

Linux / macOS:

```bash
python3 -m venv venv
source venv/bin/activate
```

**3. Install dependencies:**

```bash
pip install -r requirements.txt
```

**4. Run the application:**

```bash
python run.py
```

**Automatic port selection** is used (8000, 8001, … if busy). The console will show the URL **`http://127.0.0.1:[port]`** — open it in your browser.

**5. First run — demo game and default credentials:**

- On **first launch**, a **demo game** and admin account are created automatically.
- **Default login:** `admin`
- **Default password:** `admin`

Log in from the home page → «Вход» (Login) → enter `admin` / `admin`. Change the password in production.

---

## 🎮 Implemented Games

### Abacus (6×6)
**Classic game with sequential solving**

- **Board:** 6 topics × 6 tasks
- **Rules:** tasks in each topic must be solved in order (1→2→3→4→5→6)
- **Points:** fixed (10, 20, 30, 40, 50, 60)
- **Bonuses:**
  - Horizontal (full topic): +50 points
  - Vertical (same task number in all topics): +task value
  - Superbonus: first team gets double bonuses
- **Strategy:** order and speed matter

### Five-by-Five (5×5)
**Strategic game with line collection**

- **Board:** 5 topics × 5 tasks
- **Rules:** all tasks available immediately, choose any
- **Points:** for each correct task
- **Bonuses:** +50 points per collected line:
  - 5 horizontals (full rows)
  - 5 verticals (full columns)
  - 2 diagonals (main and anti-diagonal)
- **Maximum:** up to 12 lines = up to +600 bonus points
- **Strategy:** planning which lines to collect first

### How to Start Playing

1. Run `python run.py` and open the URL from console
2. Log in: **admin** / **admin**
3. Go to **«Игры»** (Games) → select demo game
4. Click **«Играть»** (Play) → choose team
5. Solve tasks, following cell colors:
   - 🟢 **Green** — available
   - ✅ **Checkmark** — solved correctly
   - ❌ **Cross** — solved incorrectly
   - 🔒 **Lock** — locked (Abacus only)

---

## 👥 User Roles

| Role | Description |
|------|-------------|
| **Admin** | Full access: create and edit games and teams, manage users, run tournaments. |
| **Moderator** | Run games, check answers, manage tournament flow within admin settings. |
| **Team** | Participate: view tasks, submit answers, view results. |

---

## 📁 Project Structure

```
abacus-game-web-service/
├── app/                 # Application code (main, config, database, deps, models, routes, services)
├── templates/           # Jinja2 HTML templates
├── static/              # CSS, JS
├── scripts/             # seed_demo_data.py (optional)
├── tests/               # Pytest tests
├── run.py               # Run with auto port selection
├── requirements.txt
├── README.md
├── DEMO.md
└── COURSEWORK.md
```

---

## 🧪 Testing

### Unit Tests (pytest)

```bash
pytest tests/ -v
```

Runs unit tests: authentication, CRUD operations, game logic, scoring system.

### E2E Browser Tests (Playwright)

**Installation (once):**
```bash
npm install
npx playwright install
```

**Run tests:**
```bash
npm test
```

Automated browser tests verify:
- Page accessibility
- User authentication
- Game creation (admin flow)
- Task opening and solving
- Template rendering correctness

**Additional commands:**
```bash
npm run test:headed    # With visible browser
npm run test:ui        # Interactive UI mode
```

---

## 📄 License

Educational project for coursework. No formal license. Use for educational purposes is welcome.

---

## � Contact

- **GitHub:** [Saitama4722](https://github.com/Saitama4722)
- **Telegram:** [@VadikQA](https://t.me/VadikQA)
- **Repository:** [github.com/Saitama4722/abacus-game-web-service](https://github.com/Saitama4722/abacus-game-web-service)
