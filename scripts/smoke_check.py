import sqlite3
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from db_init import init_sqlite_db
from services.sample_service import (
    borrow_sample,
    dispose_sample,
    move_sample,
    register_sample,
    return_sample,
)


def _assert(condition, message):
    if not condition:
        raise AssertionError(message)


def run():
    db_path = init_sqlite_db()
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")

    # 基础数据校验
    user_count = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    type_count = conn.execute("SELECT COUNT(*) FROM sample_types").fetchone()[0]
    _assert(user_count >= 3, "users 初始数据不足")
    _assert(type_count >= 3, "sample_types 初始数据不足")

    # 生命周期校验
    conn.execute("BEGIN")
    register_sample(conn, ("冒烟样本A", 1, 1, 1, "2026-04-01", 1, "smoke"))
    conn.commit()
    sample_id = conn.execute(
        "SELECT sample_id FROM samples WHERE sample_name = ? ORDER BY sample_id DESC LIMIT 1",
        ("冒烟样本A",),
    ).fetchone()["sample_id"]

    conn.execute("BEGIN")
    borrow_sample(conn, (sample_id, 2, "2099-01-01 12:00:00", "冒烟借用", "smoke"))
    conn.commit()

    conn.execute("BEGIN")
    return_sample(conn, (sample_id, 2, "冒烟归还"))
    conn.commit()

    conn.execute("BEGIN")
    move_sample(conn, (sample_id, 2, 1, "冒烟移位"))
    conn.commit()

    conn.execute("BEGIN")
    dispose_sample(conn, (sample_id, 1, "冒烟废弃"))
    conn.commit()

    status = conn.execute("SELECT status FROM samples WHERE sample_id = ?", (sample_id,)).fetchone()["status"]
    tx_count = conn.execute(
        "SELECT COUNT(*) FROM sample_transactions WHERE sample_id = ?",
        (sample_id,),
    ).fetchone()[0]
    _assert(status == "disposed", "样本最终状态不正确")
    _assert(tx_count == 5, "业务流水条数不正确")

    print("SMOKE_CHECK_OK")
    print(f"db_path={db_path}")
    print(f"sample_id={sample_id}, status={status}, tx_count={tx_count}")
    conn.close()


if __name__ == "__main__":
    run()
