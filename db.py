# 数据库工具模块（SQLite 版本）
import sqlite3
import threading

import pandas as pd
import streamlit as st

from audit import log_event, summarize_payload
from config import get_db_path
from db_init import init_sqlite_db
from services.sample_service import BusinessError, execute_procedure


_init_lock = threading.Lock()
_db_initialized = False


def _translate_db_error(error: Exception) -> str:
    raw_error = str(error)
    error_str = raw_error.lower()
    if "unique" in error_str:
        return "该记录已存在，请检查是否重复操作或数据冲突。"
    if "foreign key" in error_str:
        return "数据关联冲突：被引用的记录不存在，或操作违反了外键约束。"
    if "not null" in error_str:
        return "必填字段缺失，请检查所有必要字段已填写。"
    if "check constraint" in error_str:
        return "数据不符合约束条件，请检查输入值。"
    if isinstance(error, BusinessError):
        return raw_error
    return raw_error


def _normalize_params(params=None):
    if params is None:
        return ()
    if isinstance(params, (list, tuple)):
        return tuple(params)
    return (params,)


def _adapt_sql(sql: str) -> str:
    # 兼容旧代码中的 MySQL 参数占位符 %s
    return sql.replace("%s", "?")


def ensure_db_ready() -> None:
    global _db_initialized
    if _db_initialized:
        return
    with _init_lock:
        if _db_initialized:
            return
        init_sqlite_db()
        _db_initialized = True


def get_connection() -> sqlite3.Connection:
    ensure_db_ready()
    db_path = get_db_path()
    try:
        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn
    except Exception as e:
        st.error(f"数据库连接失败: {_translate_db_error(e)}")
        st.stop()
        raise


def query_df(sql, params=None):
    conn = get_connection()
    try:
        df = pd.read_sql_query(_adapt_sql(sql), conn, params=_normalize_params(params))
        return df
    finally:
        conn.close()


def fetch_all(sql, params=None):
    conn = get_connection()
    try:
        rows = conn.execute(_adapt_sql(sql), _normalize_params(params)).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def fetch_one(sql, params=None):
    rows = fetch_all(sql, params)
    return rows[0] if rows else None


def fetch_scalar(sql, params=None, default=None):
    row = fetch_one(sql, params)
    if not row:
        return default
    return next(iter(row.values()))


def execute(sql, params=None):
    conn = get_connection()
    try:
        conn.execute(_adapt_sql(sql), _normalize_params(params))
        conn.commit()
        return True
    except Exception as e:
        conn.rollback()
        st.error(_translate_db_error(e))
        return False
    finally:
        conn.close()


def execute_action(sql, params=None):
    conn = get_connection()
    try:
        conn.execute(_adapt_sql(sql), _normalize_params(params))
        conn.commit()
        log_event("db_write", "execute_action", "success", detail=summarize_payload(sql))
        return True, None
    except Exception as e:
        conn.rollback()
        msg = _translate_db_error(e)
        log_event("db_write", "execute_action", "failure", detail=f"{summarize_payload(sql)} | {msg}")
        return False, msg
    finally:
        conn.close()


def call_procedure(name, args=None):
    conn = get_connection()
    try:
        conn.execute("BEGIN")
        execute_procedure(conn, name, _normalize_params(args))
        conn.commit()
        log_event("business_write", name, "success", detail=summarize_payload(args))
        return True, None
    except Exception as e:
        conn.rollback()
        msg = _translate_db_error(e)
        log_event("business_write", name, "failure", detail=msg)
        return False, msg
    finally:
        conn.close()