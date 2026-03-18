"""
FastAPI application: routes, static files, Jinja2 templates, error handlers, logging.

Abacus Game — web service for creating and conducting mathematical games.
"""

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.sessions import SessionMiddleware

from app.config import settings
from app.database import SessionLocal, init_db
from app.routes import admin, auth, games, teams

# Import models so they are registered with Base.metadata before init_db()
from app import models  # noqa: F401

# Paths relative to project root (parent of app/)
PROJECT_ROOT = Path(__file__).resolve().parent.parent
TEMPLATES_DIR = PROJECT_ROOT / "templates"
STATIC_DIR = PROJECT_ROOT / "static"

# Logging: level from LOG_LEVEL env or DEBUG setting; format with timestamp for debugging
_LOG_LEVEL = getattr(logging, settings.log_level, logging.INFO)
logging.basicConfig(
    level=_LOG_LEVEL,
    format="%(asctime)s - %(levelname)s - %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    On startup: ensure static dirs exist, create database tables, seed default admin if no users.
    On shutdown: log and exit.
    """
    logger.info("Starting up: creating database tables if needed.")
    # Ensure static directories exist so /static/ mount and CSS/JS links work
    try:
        (PROJECT_ROOT / "static").mkdir(exist_ok=True)
        (PROJECT_ROOT / "static" / "css").mkdir(exist_ok=True)
        (PROJECT_ROOT / "static" / "js").mkdir(exist_ok=True)
        _style = PROJECT_ROOT / "static" / "css" / "style.css"
        if not _style.exists():
            _style.write_text("/* Custom styles. Bootstrap 5 covers most needs. */\nfooter { margin-top: auto; }\n", encoding="utf-8")
    except OSError as e:
        logger.warning("Could not ensure static dirs: %s", e)

    try:
        init_db()
    except Exception as e:
        logger.exception("Database initialization failed: %s", e)
        raise

    # Seed default admin user if no users exist (for initial run)
    try:
        import bcrypt
        from app.models import User

        db = SessionLocal()
        try:
            if db.query(User).count() == 0:
                admin_user = User(
                    username="admin",
                    password_hash=bcrypt.hashpw(
                        b"admin", bcrypt.gensalt()
                    ).decode("utf-8"),
                    role="admin",
                )
                db.add(admin_user)
                db.commit()
                logger.info(
                    "Seeded default admin user (username: admin, password: admin)."
                )
        finally:
            db.close()
    except Exception as e:
        logger.exception("Failed to seed default admin: %s", e)
        # Do not raise; app can still run, admin can be created manually

    # Seed demo game if no games exist (for immediate gameplay)
    try:
        from app.models import Game
        from app.seed_demo import seed_demo_data

        db = SessionLocal()
        try:
            if db.query(Game).count() == 0:
                created, _msg = seed_demo_data()
                if created:
                    logger.info(
                        "Demo game seeded. Login: admin / admin. Go to Games → Демо-игра Абакус → Играть"
                    )
                    print("")
                    print("  Демо-игра создана! Логин: admin / admin")
                    print("  Перейдите в Игры → Демо-игра Абакус → Играть")
                    print("")
        finally:
            db.close()
    except Exception as e:
        logger.exception("Failed to seed demo data: %s", e)

    yield
    logger.info("Shutting down.")


app = FastAPI(
    title=settings.project_name,
    description="Web service for creating and conducting mathematical games (Abacus: 6×6 tasks).",
    lifespan=lifespan,
)

# Middleware order: last added runs first on request. We need SessionMiddleware to run
# first so that request.scope["session"] is set before we read it. So we add our
# add_request_state middleware first (so it runs after SessionMiddleware).
@app.middleware("http")
async def add_request_state(request: Request, call_next):
    """
    Load current user from session, flash messages, and ensure CSRF token for templates.
    If session is not in scope (e.g. some test clients), use empty state.
    """
    request.state.user = None
    session = request.scope.get("session") if "session" in request.scope else None
    if session is not None:
        request.state.flash = session.pop("flash", [])
        user_id = session.get("user_id")
        if user_id is not None:
            db = SessionLocal()
            try:
                from app.models import User

                user = db.get(User, user_id)
                if user is not None:
                    request.state.user = user
            except Exception as e:
                logger.warning("Failed to load user from session: %s", e)
            finally:
                db.close()

        if "csrf_token" not in session:
            import secrets
            session["csrf_token"] = secrets.token_hex(32)
    else:
        request.state.flash = []

    return await call_next(request)


# Session middleware (must run before our add_request_state so session is in scope).
# Explicit cookie settings ensure the session cookie is set and sent back on redirect (e.g. after login).
SESSION_MAX_AGE = 14 * 24 * 60 * 60  # 14 days
app.add_middleware(
    SessionMiddleware,
    secret_key=settings.secret_key,
    session_cookie="session",
    max_age=SESSION_MAX_AGE,
    path="/",
    same_site="lax",
    https_only=False,
)


# Mount static files (CSS, JS)
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
else:
    logger.warning("Static directory not found: %s", STATIC_DIR)

# Jinja2 templates: inject current user into every template so navbar shows logged-in state
def add_user_to_context(request: Request) -> dict:
    """Context processor: make 'user' available in all templates (from request.state)."""
    return {"user": getattr(request.state, "user", None)}


templates = Jinja2Templates(
    directory=str(TEMPLATES_DIR),
    context_processors=[add_user_to_context],
)

# Include routers
app.include_router(auth.router)
app.include_router(admin.router)
app.include_router(games.router)
app.include_router(teams.router)


@app.get("/", response_class=HTMLResponse)
async def index(request: Request) -> HTMLResponse:
    """Render home page."""
    return templates.TemplateResponse("index.html", {"request": request})


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(
    request: Request, exc: StarletteHTTPException
) -> HTMLResponse:
    """
    Return HTML error pages for 404 and 5xx when raised as HTTPException.
    """
    if exc.status_code == 404:
        return templates.TemplateResponse(
            "errors/404.html",
            {"request": request},
            status_code=404,
        )
    if exc.status_code >= 500:
        logger.exception("HTTP %s: %s", exc.status_code, exc.detail)
        return templates.TemplateResponse(
            "errors/500.html",
            {"request": request},
            status_code=exc.status_code,
        )
    raise exc


@app.exception_handler(Exception)
async def server_error_handler(
    request: Request, exc: Exception
) -> HTMLResponse:
    """
    Catch-all for unhandled exceptions: return 500 page and log.
    """
    from sqlalchemy.exc import IntegrityError
    if isinstance(exc, IntegrityError):
        logger.error("Database integrity error: %s - Request: %s %s", exc, request.method, request.url.path)
    logger.exception("Unhandled exception: %s", exc)
    return templates.TemplateResponse(
        "errors/500.html",
        {"request": request},
        status_code=500,
    )
