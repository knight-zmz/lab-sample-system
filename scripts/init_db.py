import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from db_init import init_sqlite_db


if __name__ == "__main__":
    path = init_sqlite_db()
    print(f"SQLite initialized at: {path}")
