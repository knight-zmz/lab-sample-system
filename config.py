import os
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"


def get_db_path() -> Path:
    raw = os.getenv("APP_DB_PATH", "").strip()
    if raw:
        return Path(raw).expanduser().resolve()
    return DATA_DIR / "lab_sample.db"


def get_default_admin_username() -> str:
    return os.getenv("APP_DEFAULT_ADMIN_USER", "admin").strip() or "admin"


def get_default_admin_password() -> str:
    return os.getenv("APP_DEFAULT_ADMIN_PASSWORD", "admin123").strip() or "admin123"


def is_auto_seed_enabled() -> bool:
    value = os.getenv("APP_AUTO_SEED", "1").strip().lower()
    return value not in {"0", "false", "no"}
