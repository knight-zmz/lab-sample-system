import streamlit as st

from db import query_df
from permissions import require_permission
from utils.streamlit_compat import safe_dataframe


def run():
    if not require_permission("audit.view", "仅管理员可查看系统审计日志。"):
        return

    st.subheader("系统审计日志")
    st.caption("该页面展示系统级审计事件，区别于样本业务流水。")

    df = query_df(
        """
        SELECT
            audit_id,
            event_type,
            actor_username,
            action,
            target_type,
            target_id,
            status,
            detail,
            created_at
        FROM audit_logs
        ORDER BY audit_id DESC
        LIMIT 1000
        """
    )
    if df.empty:
        st.info("暂无审计日志。")
        return

    keyword = st.text_input("搜索审计日志", placeholder="按用户名、动作、详情筛选")
    status_options = ["全部"] + sorted(df["status"].dropna().unique().tolist())
    selected_status = st.selectbox("按状态筛选", status_options)

    filtered = df.copy()
    if keyword.strip():
        mask = (
            filtered["actor_username"].fillna("").str.contains(keyword, case=False)
            | filtered["action"].fillna("").str.contains(keyword, case=False)
            | filtered["detail"].fillna("").str.contains(keyword, case=False)
        )
        filtered = filtered[mask]
    if selected_status != "全部":
        filtered = filtered[filtered["status"] == selected_status]

    safe_dataframe(st, filtered, width="stretch")
