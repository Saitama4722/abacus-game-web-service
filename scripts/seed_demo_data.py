"""
Seed demo data for immediate gameplay.

Run from project root:
  python scripts/seed_demo_data.py

Creates a demo game "Демо-игра Абакус" with 2 teams, 6 topics, 6 tasks per topic.
Skips creation if demo data already exists.
Returns 0 if data was created, 1 if skipped (already exists), 2 on error.
"""

import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(PROJECT_ROOT)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


def main() -> int:
    try:
        from app.seed_demo import seed_demo_data

        created, msg = seed_demo_data()
        print(msg)
        return 0 if created else 1
    except Exception as e:
        print(f"Ошибка: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
