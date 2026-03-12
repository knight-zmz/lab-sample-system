#数据库工具模块
import os
import pymysql
import pandas as pd
import streamlit as st


def get_connection():
    try:
        conn = pymysql.connect(
            host=os.getenv("DB_HOST", "127.0.0.1"),
            user=os.getenv("DB_USER", "root"),
            password=os.getenv("DB_PASSWORD", "root1234"),
            database=os.getenv("DB_NAME", "lab_sample_db"),
            port=int(os.getenv("DB_PORT", 3306)),
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