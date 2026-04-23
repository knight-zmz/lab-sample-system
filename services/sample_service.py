from datetime import date, datetime
import sqlite3


class BusinessError(Exception):
    pass


def _now_iso():
    return datetime.now().replace(microsecond=0).isoformat(sep=" ")


def _to_date_text(value):
    if value is None:
        return None
    if isinstance(value, date):
        return value.isoformat()
    return str(value)


def _to_datetime_text(value):
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.replace(microsecond=0).isoformat(sep=" ")
    return str(value)


def register_sample(conn, args):
    (
        sample_name,
        type_id,
        project_id,
        location_id,
        collected_date,
        user_id,
        remark,
    ) = args
    if not str(sample_name or "").strip():
        raise BusinessError("样本名称不能为空")

    row = conn.execute("SELECT 1 FROM sample_types WHERE type_id = ?", (type_id,)).fetchone()
    if not row:
        raise BusinessError("样本类型不存在")

    if project_id is not None:
        row = conn.execute("SELECT 1 FROM projects WHERE project_id = ?", (project_id,)).fetchone()
        if not row:
            raise BusinessError("所属项目不存在")

    row = conn.execute("SELECT 1 FROM storage_locations WHERE location_id = ?", (location_id,)).fetchone()
    if not row:
        raise BusinessError("存储位置不存在")

    if user_id is not None:
        row = conn.execute("SELECT 1 FROM users WHERE user_id = ?", (user_id,)).fetchone()
        if not row:
            raise BusinessError("登记用户不存在")

    collected_text = _to_date_text(collected_date)
    if collected_text is not None and collected_text > date.today().isoformat():
        raise BusinessError("采集日期不能晚于当前日期")

    now_text = _now_iso()
    cursor = conn.execute(
        """
        INSERT INTO samples (sample_code, sample_name, type_id, project_id, location_id, status, collected_date, created_at)
        VALUES (?, ?, ?, ?, ?, 'available', ?, ?)
        """,
        (f"PENDING-{int(datetime.now().timestamp())}", str(sample_name).strip(), type_id, project_id, location_id, collected_text, now_text),
    )
    sample_id = cursor.lastrowid
    sample_code = f"S{date.today().strftime('%Y%m%d')}-{sample_id:04d}"
    conn.execute("UPDATE samples SET sample_code = ? WHERE sample_id = ?", (sample_code, sample_id))
    conn.execute(
        """
        INSERT INTO sample_transactions (sample_id, user_id, action_type, from_location_id, to_location_id, action_time, remark)
        VALUES (?, ?, 'CREATE', NULL, ?, ?, ?)
        """,
        (sample_id, user_id, location_id, now_text, remark or "样本登记入库"),
    )


def borrow_sample(conn, args):
    sample_id, user_id, expected_return_time, purpose, note = args
    row = conn.execute("SELECT 1 FROM users WHERE user_id = ?", (user_id,)).fetchone()
    if not row:
        raise BusinessError("借用用户不存在")

    sample = conn.execute(
        "SELECT status, location_id FROM samples WHERE sample_id = ?",
        (sample_id,),
    ).fetchone()
    if not sample:
        raise BusinessError("样本不存在")
    if sample["status"] == "borrowed":
        raise BusinessError("样本当前已借出，不能重复借用")
    if sample["status"] == "disposed":
        raise BusinessError("样本已废弃，不能借用")

    active_borrow = conn.execute(
        """
        SELECT 1 FROM borrow_records
        WHERE sample_id = ? AND status IN ('borrowed', 'overdue')
        LIMIT 1
        """,
        (sample_id,),
    ).fetchone()
    if active_borrow:
        raise BusinessError("该样本存在未结束的借用记录")

    expected_text = _to_datetime_text(expected_return_time)
    now_text = _now_iso()
    if expected_text is not None and expected_text <= now_text:
        raise BusinessError("预计归还时间必须晚于当前时间")

    conn.execute(
        """
        INSERT INTO borrow_records (
            sample_id, user_id, borrow_time, expected_return_time,
            actual_return_time, status, purpose, note
        ) VALUES (?, ?, ?, ?, NULL, 'borrowed', ?, ?)
        """,
        (sample_id, user_id, now_text, expected_text, purpose, note),
    )
    conn.execute("UPDATE samples SET status = 'borrowed' WHERE sample_id = ?", (sample_id,))
    conn.execute(
        """
        INSERT INTO sample_transactions (sample_id, user_id, action_type, from_location_id, to_location_id, action_time, remark)
        VALUES (?, ?, 'BORROW', ?, NULL, ?, ?)
        """,
        (sample_id, user_id, sample["location_id"], now_text, note or "样本借出"),
    )


def return_sample(conn, args):
    sample_id, user_id, note = args
    if user_id is not None:
        row = conn.execute("SELECT 1 FROM users WHERE user_id = ?", (user_id,)).fetchone()
        if not row:
            raise BusinessError("归还操作用户不存在")

    sample = conn.execute(
        "SELECT status, location_id FROM samples WHERE sample_id = ?",
        (sample_id,),
    ).fetchone()
    if not sample:
        raise BusinessError("样本不存在")
    if sample["status"] != "borrowed":
        raise BusinessError("样本当前并非借出状态，不能执行归还")

    borrow = conn.execute(
        """
        SELECT borrow_id, note
        FROM borrow_records
        WHERE sample_id = ? AND status IN ('borrowed', 'overdue')
        ORDER BY borrow_time DESC
        LIMIT 1
        """,
        (sample_id,),
    ).fetchone()
    if not borrow:
        raise BusinessError("未找到有效的借用记录，无法归还")

    now_text = _now_iso()
    old_note = borrow["note"] or ""
    if note:
        merged_note = f"{old_note}；{note}" if old_note else note
    else:
        merged_note = old_note or "样本已归还"

    conn.execute(
        """
        UPDATE borrow_records
        SET actual_return_time = ?, status = 'returned', note = ?
        WHERE borrow_id = ?
        """,
        (now_text, merged_note, borrow["borrow_id"]),
    )
    conn.execute("UPDATE samples SET status = 'available' WHERE sample_id = ?", (sample_id,))
    conn.execute(
        """
        INSERT INTO sample_transactions (sample_id, user_id, action_type, from_location_id, to_location_id, action_time, remark)
        VALUES (?, ?, 'RETURN', NULL, ?, ?, ?)
        """,
        (sample_id, user_id, sample["location_id"], now_text, note or "样本归还入库"),
    )


def move_sample(conn, args):
    sample_id, new_location_id, user_id, note = args
    if user_id is not None:
        row = conn.execute("SELECT 1 FROM users WHERE user_id = ?", (user_id,)).fetchone()
        if not row:
            raise BusinessError("操作用户不存在")
    row = conn.execute("SELECT 1 FROM storage_locations WHERE location_id = ?", (new_location_id,)).fetchone()
    if not row:
        raise BusinessError("新存储位置不存在")

    sample = conn.execute(
        "SELECT status, location_id FROM samples WHERE sample_id = ?",
        (sample_id,),
    ).fetchone()
    if not sample:
        raise BusinessError("样本不存在")
    if sample["status"] == "borrowed":
        raise BusinessError("样本正在借出中，不能直接移位")
    if sample["status"] == "disposed":
        raise BusinessError("样本已废弃，不能移位")
    if sample["location_id"] == new_location_id:
        raise BusinessError("新旧位置相同，无需移位")

    now_text = _now_iso()
    conn.execute("UPDATE samples SET location_id = ? WHERE sample_id = ?", (new_location_id, sample_id))
    conn.execute(
        """
        INSERT INTO sample_transactions (sample_id, user_id, action_type, from_location_id, to_location_id, action_time, remark)
        VALUES (?, ?, 'MOVE', ?, ?, ?, ?)
        """,
        (sample_id, user_id, sample["location_id"], new_location_id, now_text, note or "样本位置调整"),
    )


def dispose_sample(conn, args):
    sample_id, user_id, note = args
    if user_id is not None:
        row = conn.execute("SELECT 1 FROM users WHERE user_id = ?", (user_id,)).fetchone()
        if not row:
            raise BusinessError("操作用户不存在")

    sample = conn.execute(
        "SELECT status, location_id FROM samples WHERE sample_id = ?",
        (sample_id,),
    ).fetchone()
    if not sample:
        raise BusinessError("样本不存在")
    if sample["status"] == "borrowed":
        raise BusinessError("样本处于借出状态，必须归还后才能废弃")
    if sample["status"] == "disposed":
        raise BusinessError("样本已废弃，无需重复操作")

    now_text = _now_iso()
    conn.execute("UPDATE samples SET status = 'disposed' WHERE sample_id = ?", (sample_id,))
    conn.execute(
        """
        INSERT INTO sample_transactions (sample_id, user_id, action_type, from_location_id, to_location_id, action_time, remark)
        VALUES (?, ?, 'DISPOSE', ?, NULL, ?, ?)
        """,
        (sample_id, user_id, sample["location_id"], now_text, note or "样本废弃处理"),
    )


PROCEDURE_DISPATCH = {
    "sp_register_sample": register_sample,
    "sp_borrow_sample": borrow_sample,
    "sp_return_sample": return_sample,
    "sp_move_sample": move_sample,
    "sp_dispose_sample": dispose_sample,
}


def execute_procedure(conn, name, args):
    proc = PROCEDURE_DISPATCH.get(name)
    if not proc:
        raise BusinessError(f"不支持的过程调用: {name}")
    proc(conn, args or ())
