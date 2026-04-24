import sqlite3
from datetime import datetime

from config import get_db_path


def log_event(
    event_type,
    action,
    status,
    detail=None,
    actor_user_id=None,
    actor_username=None,
    target_type=None,
    target_id=None,
):
    db_path = get_db_path()
    if not db_path.exists():
        return
    try:
        with sqlite3.connect(str(db_path)) as conn:
            local_created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            conn.execute(
                """
                INSERT INTO audit_logs (
                    event_type, actor_user_id, actor_username, action,
                    target_type, target_id, status, detail, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    event_type,
                    actor_user_id,
                    actor_username,
                    action,
                    target_type,
                    target_id,
                    status,
                    detail,
                    local_created_at,
                ),
            )
            conn.commit()
    except Exception:
        # 审计记录失败不应阻塞主业务流程
        return


def summarize_payload(payload, max_len=180):
    text = str(payload)
    if len(text) <= max_len:
        return text
    return f"{text[:max_len]}..."
