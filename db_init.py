from pathlib import Path
import hashlib
import os
import sqlite3

from config import (
    get_db_path,
    get_default_admin_password,
    get_default_admin_username,
    is_auto_seed_enabled,
)


def hash_password(password, salt=None):
    safe_salt = salt or os.urandom(16).hex()
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), safe_salt.encode("utf-8"), 120000)
    return f"pbkdf2_sha256${safe_salt}${digest.hex()}"


def _schema_path():
    return Path(__file__).resolve().parent / "sql" / "init_sqlite.sql"


def init_sqlite_db():
    db_path = get_db_path()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    schema_sql = _schema_path().read_text(encoding="utf-8")

    with sqlite3.connect(str(db_path)) as conn:
        conn.execute("PRAGMA foreign_keys = ON")
        conn.executescript(schema_sql)
        _migrate_audit_logs_created_at_default(conn)
        if is_auto_seed_enabled():
            seed_basic_data(conn)
        conn.commit()
    return db_path


def _migrate_audit_logs_created_at_default(conn):
    """
    历史数据库可能将 audit_logs.created_at 默认值建成了 CURRENT_TIMESTAMP（UTC）。
    这里做一次无损迁移，统一为本地时区默认值。
    """
    row = conn.execute(
        "SELECT sql FROM sqlite_master WHERE type='table' AND name='audit_logs'"
    ).fetchone()
    if not row or not row[0]:
        return
    ddl = str(row[0]).lower()
    if "datetime('now', 'localtime')" in ddl:
        return

    conn.execute("PRAGMA foreign_keys = OFF")
    try:
        conn.execute("ALTER TABLE audit_logs RENAME TO audit_logs_old")
        conn.execute(
            """
            CREATE TABLE audit_logs (
                audit_id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_type TEXT NOT NULL,
                actor_user_id INTEGER,
                actor_username TEXT,
                action TEXT NOT NULL,
                target_type TEXT,
                target_id TEXT,
                status TEXT NOT NULL CHECK (status IN ('success', 'failure', 'denied', 'error')),
                detail TEXT,
                created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
            )
            """
        )
        conn.execute(
            """
            INSERT INTO audit_logs (
                audit_id, event_type, actor_user_id, actor_username, action,
                target_type, target_id, status, detail, created_at
            )
            SELECT
                audit_id, event_type, actor_user_id, actor_username, action,
                target_type, target_id, status, detail, created_at
            FROM audit_logs_old
            """
        )
        conn.execute("DROP TABLE audit_logs_old")
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_audit_event_created ON audit_logs(event_type, created_at)"
        )
    finally:
        conn.execute("PRAGMA foreign_keys = ON")


def seed_basic_data(conn):
    admin_user = get_default_admin_username()
    admin_pass = get_default_admin_password()
    admin_hash = hash_password(admin_pass)
    staff_hash = hash_password("staff123")
    viewer_hash = hash_password("viewer123")

    conn.execute(
        """
        INSERT INTO users (username, real_name, role, password_hash, is_active)
        VALUES (?, ?, ?, ?, 1)
        ON CONFLICT(username) DO NOTHING
        """,
        (admin_user, "系统管理员", "admin", admin_hash),
    )
    conn.execute(
        """
        INSERT INTO users (username, real_name, role, password_hash, is_active)
        VALUES (?, ?, ?, ?, 1)
        ON CONFLICT(username) DO NOTHING
        """,
        ("staff", "实验员", "staff", staff_hash),
    )
    conn.execute(
        """
        INSERT INTO users (username, real_name, role, password_hash, is_active)
        VALUES (?, ?, ?, ?, 1)
        ON CONFLICT(username) DO NOTHING
        """,
        ("viewer", "访客", "viewer", viewer_hash),
    )

    conn.executemany(
        """
        INSERT INTO sample_types (type_name, description)
        VALUES (?, ?)
        ON CONFLICT(type_name) DO NOTHING
        """,
        [
            ("血液样本", "来源于实验对象的血液样本"),
            ("组织样本", "来源于心脏、肝脏等组织"),
            ("细胞样本", "培养细胞或细胞提取物"),
        ],
    )

    conn.executemany(
        """
        INSERT INTO storage_locations (location_name, description)
        VALUES (?, ?)
        ON CONFLICT(location_name) DO NOTHING
        """,
        [
            ("冰箱A-1层", "4℃冰箱第一层"),
            ("-80冰柜A-2层", "-80℃冰柜第二层"),
            ("液氮罐1号", "液氮长期保存区域"),
        ],
    )

    conn.executemany(
        """
        INSERT INTO projects (project_name, principal_investigator, start_date, end_date, description)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(project_name) DO NOTHING
        """,
        [
            ("鹿心多肽活性研究", "王老师", "2026-03-01", None, "用于研究鹿心来源样本及相关活性机制"),
            ("细胞应激实验项目", "李老师", "2026-02-20", None, "关注细胞提取物与应激响应"),
        ],
    )
