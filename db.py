#数据库工具模块
import os
import time

import pandas as pd
import pymysql
import streamlit as st


def _translate_db_error(error: Exception) -> str:
    """
    把 MySQL 异常翻译成用户友好的提示信息。
    """
    error_str = str(error).lower()
    
    if "1062" in error_str or "unique" in error_str or "duplicate" in error_str:
        return "该记录已存在，请检查是否重复操作或数据冲突。"
    elif "1452" in error_str or "foreign key" in error_str:
        return "数据关联冲突：被引用的记录不存在，或操作违反了外键约束。"
    elif "1451" in error_str:
        return "无法删除：该记录仍被其他数据引用，请先处理关联记录。"
    elif "1406" in error_str or "truncated" in error_str:
        return "输入数据过长，请检查字段内容长度。"
    elif "1364" in error_str or "not enough" in error_str:
        return "必填字段缺失，请检查所有必要字段已填写。"
    elif "45000" in error_str:
        # 自定义业务错误（来自存储过程 SIGNAL）
        if "采集日期" in error_str:
            return "采集日期不能晚于当前日期。"
        elif "存在" in error_str:
            return error_str
        elif "不能" in error_str:
            return error_str
        return str(error)
    elif "connection" in error_str or "timeout" in error_str:
        return "数据库连接失败，请检查数据库服务是否在线。"
    else:
        return str(error)


def _get_secret(key: str, default: str) -> str:
    """
    优先读取 Streamlit secrets，其次读取环境变量，最后用默认值。
    保证始终返回 str，避免类型检查器关于可选类型的报错。
    """
    try:
        if key in st.secrets:
            return str(st.secrets[key])
    except Exception:
        pass
    value = os.getenv(key)
    if value is not None:
        return value
    return default


def get_connection():
    try:
        conn = pymysql.connect(
            host=_get_secret("DB_HOST", "127.0.0.1"),
            user=_get_secret("DB_USER", "root"),
            password=_get_secret("DB_PASSWORD", "root1234"),
            database=_get_secret("DB_NAME", "lab_sample_db"),
            port=int(_get_secret("DB_PORT", "3306")),
            charset="utf8mb4"
        )
        return conn
    except Exception as e:
        st.error(f"数据库连接失败: {e}")
        st.stop()


def _normalize_params(params=None):
    if params is None:
        return ()
    if isinstance(params, (list, tuple)):
        return tuple(params)
    return (params,)


def query_df(sql, params=None):
    conn = get_connection()
    try:
        df = pd.read_sql(sql, conn, params=params)
        return df
    finally:
        conn.close()


def fetch_all(sql, params=None):
    conn = get_connection()
    cursor = None
    try:
        cursor = conn.cursor(cursor=pymysql.cursors.DictCursor)
        cursor.execute(sql, _normalize_params(params))
        return cursor.fetchall()
    finally:
        if cursor is not None:
            cursor.close()
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
    cursor = None
    try:
        cursor = conn.cursor()
        cursor.execute(sql, _normalize_params(params))
        conn.commit()
        return True
    except Exception as e:
        conn.rollback()
        st.error(str(e))
        return False
    finally:
        if cursor is not None:
            cursor.close()
        conn.close()


def execute_action(sql, params=None):
    conn = get_connection()
    cursor = None
    try:
        cursor = conn.cursor()
        cursor.execute(sql, _normalize_params(params))
        conn.commit()
        return True, None
    except Exception as e:
        conn.rollback()
        return False, _translate_db_error(e)
    finally:
        if cursor is not None:
            cursor.close()
        conn.close()


def call_procedure(name, args=None):
    conn = get_connection()
    cursor = None
    try:
        cursor = conn.cursor()
        cursor.callproc(name, _normalize_params(args))
        conn.commit()
        return True, None
    except Exception as e:
        conn.rollback()
        return False, _translate_db_error(e)
    finally:
        if cursor is not None:
            cursor.close()
        conn.close()