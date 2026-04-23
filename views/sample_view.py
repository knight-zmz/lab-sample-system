import streamlit as st

from db import query_df
from permissions import require_permission
from utils.streamlit_compat import safe_dataframe


def run():
    if not require_permission("sample.view", "仅允许查看样本信息。"):
        return

    st.subheader("样本信息总览")

    df = query_df(
        """
        SELECT
            sample_id,
            sample_code,
            sample_name,
            type_name,
            project_name,
            location_name,
            status,
            collected_date,
            created_at
        FROM v_sample_detail
        ORDER BY created_at DESC, sample_id DESC
        """
    )

    if df.empty:
        st.info("当前还没有样本数据。")
        return

    keyword = st.text_input("搜索样本编号或名称")

    type_options = ["全部"] + sorted(df["type_name"].dropna().unique().tolist())
    status_options = ["全部"] + sorted(df["status"].dropna().unique().tolist())
    project_values = [value for value in df["project_name"].dropna().unique().tolist() if value]
    project_options = ["全部"] + sorted(project_values)

    filter_col1, filter_col2, filter_col3 = st.columns(3)
    with filter_col1:
        selected_type = st.selectbox("按样本类型筛选", type_options)
    with filter_col2:
        selected_status = st.selectbox("按当前状态筛选", status_options)
    with filter_col3:
        selected_project = st.selectbox("按项目筛选", project_options)

    filtered_df = df.copy()
    if keyword.strip():
        keyword_mask = (
            filtered_df["sample_code"].fillna("").str.contains(keyword, case=False)
            | filtered_df["sample_name"].fillna("").str.contains(keyword, case=False)
        )
        filtered_df = filtered_df[keyword_mask]

    if selected_type != "全部":
        filtered_df = filtered_df[filtered_df["type_name"] == selected_type]
    if selected_status != "全部":
        filtered_df = filtered_df[filtered_df["status"] == selected_status]
    if selected_project != "全部":
        filtered_df = filtered_df[filtered_df["project_name"] == selected_project]

    summary_col1, summary_col2, summary_col3, summary_col4 = st.columns(4)
    summary_col1.metric("样本总数", len(filtered_df))
    summary_col2.metric("在库可用", int((filtered_df["status"] == "available").sum()))
    summary_col3.metric("借出中", int((filtered_df["status"] == "borrowed").sum()))
    summary_col4.metric("已废弃", int((filtered_df["status"] == "disposed").sum()))

    safe_dataframe(st, filtered_df, width="stretch")