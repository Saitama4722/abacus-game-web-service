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

Веб-сервис для **создания и проведения математических игр** — курсовая работа. Реализована игра **«Абака»** (Математический квадрат): создание игр, управление командами, проведение турниров с прозрачной системой подсчёта очков.

Кратко об игре: поле 6×6 (6 тем × 6 заданий), задания в каждой теме решаются **строго по порядку**, начисляются фиксированные баллы (10, 20, 30, 40, 50, 60) и бонусы за полные строки и столбцы (горизонталь +50, вертикаль — стоимость задания, супербонус — удвоение для первой команды).

---

## ✨ Возможности

- **CRUD игр и команд** — полное создание, редактирование и удаление игр и команд
- **Редактор поля 6×6** — настройка тем и заданий для каждой игры
- **Строгие правила** — порядок решения заданий в теме, проверка ответов
- **Система очков** — баллы 10, 20, 30, 40, 50, 60; бонусы за строку (+50), столбец (стоимость задания), супербонус (удвоение для первой команды)
- **Роли** — администратор, модератор, команда (team)
- **Адаптивный интерфейс** — Bootstrap 5, интерфейс на русском языке
- **Демо при первом запуске** — автоматическое создание демо-игры и учётной записи admin/admin

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

## 🎮 Как играть

Пошаговая инструкция для первого запуска (администратор/игрок):

1. Запустите сервер: `python run.py` и откройте в браузере адрес из консоли (например `http://127.0.0.1:8000`).
2. Войдите: нажмите **«Вход»**, введите логин **`admin`** и пароль **`admin`**.
3. Перейдите в **«Игры»** и выберите **«Демо-игра Абакус»**.
4. Нажмите **«Играть»**.
5. Выберите команду (например **«Команда Альфа»** или **«Команда Бета»**).
6. На игровом поле 6×6 ориентируйтесь по цветам ячеек:
   - 🟢 **Зелёная** — задание доступно для решения (следующее по порядку в теме).
   - ✅ **Решённое** — задание уже засчитано.
   - ❌ **Неверный ответ** — можно пробовать снова (если предусмотрено правилами).
   - 🔒 **Заблокированная** — задание пока недоступно (нужно решить предыдущее в теме).
7. **Порядок:** в каждой теме задания решаются строго по порядку: сначала 1-е, затем 2-е, …, затем 6-е.
8. **Бонусы:** после решения всех 6 заданий в теме — бонус +50 за полную строку; за полный столбец — бонус равен стоимости задания; супербонус — первой команде удвоенные бонусы.

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

## 🧪 Запуск тестов

```bash
pytest tests/ -v
```

Запускает все тесты в каталоге `tests/` с подробным выводом.

---

## 📄 Лицензия

Учебный проект для курсовой работы. Формальная лицензия не указана. Использование в образовательных целях приветствуется.

---

## 👨‍💻 Автор

- **GitHub:** [Saitama4722](https://github.com/Saitama4722)

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

**Web service for creating and conducting mathematical games** — coursework project. Implements the **«Abaca»** game (Mathematical Square): 6 topics × 6 tasks, tasks must be solved in order within each topic. Points: 10, 20, 30, 40, 50, 60. Bonuses: horizontal (full topic, +50), vertical (same task number in all topics, task value), superbonus (first team(s) get double points). Tech stack: Python, FastAPI, SQLite, SQLAlchemy (ORM), Jinja2, Bootstrap 5, Uvicorn. Features: full CRUD for games/teams, 6×6 board editor, strict gameplay rules, scoring system, admin/moderator/team roles, responsive UI in Russian, automatic demo game and admin account on first start.

---

## ✨ Features

- **Full CRUD** for games and teams
- **6×6 board editor** — configure topics and tasks per game
- **Strict rules** — tasks in order per topic, answer validation
- **Scoring** — 10, 20, 30, 40, 50, 60; row bonus +50, column bonus (task value), superbonus (double for first team)
- **Roles** — Admin, Moderator, Team
- **Responsive UI** in Russian (Bootstrap 5)
- **Auto demo** on first launch — default credentials **admin** / **admin**, demo game created automatically

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

## 🎮 How to Play

Step-by-step guide for a first-time user/admin:

1. Run `python run.py` and open the URL from the console (e.g. `http://127.0.0.1:8000`).
2. Log in: click **«Вход»**, enter **`admin`** / **`admin`**.
3. Go to **«Игры»** (Games) and select **«Демо-игра Абакус»**.
4. Click **«Играть»** (Play).
5. Choose a team (e.g. **«Команда Альфа»** or **«Команда Бета»**).
6. On the 6×6 board, use the color legend:
   - 🟢 **Green** — task available (next in order in the topic).
   - ✅ **Solved** — task already counted.
   - ❌ **Wrong** — incorrect answer (retry if allowed).
   - 🔒 **Locked** — task not yet available (solve the previous one in the topic first).
7. **Order:** within each topic, solve tasks **in order** (1st, then 2nd, …, then 6th).
8. **Bonuses:** after solving all 6 tasks in a topic — +50 row bonus; full column — bonus equals task value; superbonus — first team gets double.

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

## 🧪 Running Tests

```bash
pytest tests/ -v
```

Runs all tests in the `tests/` directory with verbose output.

---

## 📄 License

Educational project for coursework. No formal license. Use for educational purposes is welcome.

---

## 👨‍💻 Author

- **GitHub:** [Saitama4722](https://github.com/Saitama4722)
