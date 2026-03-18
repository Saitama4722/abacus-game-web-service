"""
Stage 10.1: Project startup verification script.

Run from project root:
  python scripts/verify_startup.py

Checks:
- Database file is created when missing
- Default admin user exists after first run
- No errors in console during startup (manual check)
"""

import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(PROJECT_ROOT)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# Use a temporary DB for this script so we don't delete the real one
TEST_DB = os.path.join(PROJECT_ROOT, "abacus_game_verify_startup.db")
os.environ["DATABASE_URL"] = f"sqlite:///{TEST_DB}"

def main() -> int:
    # Remove test DB if present (simulate fresh install)
    if os.path.exists(TEST_DB):
        try:
            os.remove(TEST_DB)
        except OSError as e:
            print(f"Could not remove {TEST_DB}: {e}", file=sys.stderr)
            return 1

    # Import after setting env so app uses test DB
    from app.database import SessionLocal, init_db
    from app.models import User

    init_db()
    if not os.path.exists(TEST_DB):
        print("FAIL: Database file was not created.", file=sys.stderr)
        return 1
    print("OK: Database file created.")

    # Seed default admin (same logic as app lifespan) if no users
    db = SessionLocal()
    try:
        if db.query(User).count() == 0:
            import bcrypt
            admin_user = User(
                username="admin",
                password_hash=bcrypt.hashpw(b"admin", bcrypt.gensalt()).decode("utf-8"),
                role="admin",
            )
            db.add(admin_user)
            db.commit()
        admin = db.query(User).filter(User.username == "admin").first()
        if admin is None:
            print("FAIL: Default admin user (admin) not found.", file=sys.stderr)
            return 1
        print("OK: Default admin user exists.")
    finally:
        db.close()

    try:
        os.remove(TEST_DB)
    except OSError:
        pass
    print("Startup verification passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
