#数据库工具模块
import os
import pymysql
import pandas as pd
import streamlit as st


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


def query_df(sql, params=None):
    conn = get_connection()
    try:
        df = pd.read_sql(sql, conn, params=params)
        return df
    finally:
        conn.close()


def execute(sql, params=None):
    conn = get_connection()
    cursor = None
    try:
        cursor = conn.cursor()
        cursor.execute(sql, params)
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