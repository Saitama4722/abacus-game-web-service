"""
Authentication routes: login page, login/logout logic with session and password verification.
"""

import logging
from pathlib import Path
from typing import Annotated
from urllib.parse import quote

import bcrypt
from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["authentication"])
templates = Jinja2Templates(
    directory=str(Path(__file__).resolve().parent.parent.parent / "templates")
)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against a bcrypt hash."""
    try:
        return bcrypt.checkpw(
            plain_password.encode("utf-8"),
            hashed_password.encode("utf-8")
            if isinstance(hashed_password, str)
            else hashed_password,
        )
    except Exception:
        return False


def hash_password(password: str) -> str:
    """Hash a password with bcrypt; returns string suitable for storing in DB."""
    return bcrypt.hashpw(
        password.encode("utf-8"), bcrypt.gensalt()
    ).decode("utf-8")


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request) -> HTMLResponse:
    """Render login form. Pass 'next' URL for redirect after successful login."""
    next_url = request.query_params.get("next", "/")
    logger.info("GET /auth/login - next=%s - Status: 200", next_url)
    return templates.TemplateResponse(
        "login.html", {"request": request, "next_url": next_url}
    )


@router.post("/login", response_class=RedirectResponse)
async def login_submit(
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    username: str = Form(...),
    password: str = Form(...),
    next_url: str = Form(default="/", alias="next"),
) -> RedirectResponse:
    """
    Validate username/password; on success set session and redirect to next_url.
    On failure redirect back to login with error=invalid.
    """
    logger.info("POST /auth/login - username=%s next=%s", username, next_url)
    user = db.query(User).filter(User.username == username).first()
    if user is None or not verify_password(password, user.password_hash):
        logger.warning("POST /auth/login - Failed login attempt - username=%s - Result: failure - Status: 303", username)
        return RedirectResponse(
            url=f"/auth/login?error=invalid&next={quote(next_url, safe='/')}", status_code=303
        )
    request.session["user_id"] = user.id
    logger.info("POST /auth/login - User %s (id=%s role=%s) logged in - Result: success - Status: 303", user.username, user.id, user.role)
    # Prevent open redirect: allow only relative paths (keeps cookie on same origin)
    if not next_url.startswith("/") or next_url.startswith("//"):
        next_url = "/"
    # Use relative URL so redirect stays same-origin and browser keeps session cookie
    return RedirectResponse(url=next_url, status_code=303)


@router.get("/logout", response_class=RedirectResponse)
async def logout(request: Request) -> RedirectResponse:
    """Clear session and redirect to home."""
    user_id = request.session.get("user_id")
    logger.info("GET /auth/logout - user_id=%s", user_id)
    if "user_id" in request.session:
        request.session.clear()
        logger.info("GET /auth/logout - User logged out - Result: success - Status: 303")
    return RedirectResponse(url="/", status_code=303)
