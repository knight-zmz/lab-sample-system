import streamlit as st

from db import query_df
from permissions import require_permission
from utils.streamlit_compat import safe_dataframe

def run():
    if not require_permission("record.view", "当前角色仅允许访问授权记录页面。"):
        return

    st.subheader("出入库记录")
    st.caption("查看当前借用单据和样本历史流水，所有数据直接对齐数据库视图与业务表。")

    borrowed_df = query_df(
        """
        SELECT
            borrow_id,
            sample_code,
            sample_name,
            borrower_name,
            borrow_time,
            expected_return_time,
            status,
            purpose,
            note
        FROM v_current_borrowed_samples
        ORDER BY borrow_time DESC
        """
    )

    transactions_df = query_df(
        """
        SELECT
            st.transaction_id,
            s.sample_code,
            s.sample_name,
            st.action_type,
            u.real_name AS operator_name,
            fl.location_name AS from_location_name,
            tl.location_name AS to_location_name,
            st.action_time,
            st.remark
        FROM sample_transactions st
        JOIN samples s
            ON st.sample_id = s.sample_id
        LEFT JOIN users u
            ON st.user_id = u.user_id
        LEFT JOIN storage_locations fl
            ON st.from_location_id = fl.location_id
        LEFT JOIN storage_locations tl
            ON st.to_location_id = tl.location_id
        ORDER BY st.action_time DESC, st.transaction_id DESC
        """
    )

    borrowed_tab, transaction_tab = st.tabs(["当前借用记录", "历史流水"])

    with borrowed_tab:
        if borrowed_df.empty:
            st.info("当前没有处于借用中的样本。")
        else:
            keyword = st.text_input("搜索借用样本", placeholder="按样本编号、名称或借用人筛选", key="borrowed_keyword")
            filtered_borrowed = borrowed_df.copy()
            if keyword.strip():
                mask = (
                    filtered_borrowed["sample_code"].fillna("").str.contains(keyword, case=False)
                    | filtered_borrowed["sample_name"].fillna("").str.contains(keyword, case=False)
                    | filtered_borrowed["borrower_name"].fillna("").str.contains(keyword, case=False)
                )
                filtered_borrowed = filtered_borrowed[mask]

            metric_col1, metric_col2 = st.columns(2)
            metric_col1.metric("当前借用单数", len(filtered_borrowed))
            metric_col2.metric("逾期单数", int((filtered_borrowed["status"] == "overdue").sum()))
            safe_dataframe(st, filtered_borrowed, width="stretch")

    with transaction_tab:
        if transactions_df.empty:
            st.info("当前还没有样本历史流水。")
        else:
            keyword = st.text_input("搜索流水记录", placeholder="按样本编号、名称或备注筛选", key="transaction_keyword")
            action_options = ["全部"] + sorted(transactions_df["action_type"].dropna().unique().tolist())
            selected_action = st.selectbox("按动作类型筛选", action_options)

            filtered_transactions = transactions_df.copy()
            if keyword.strip():
                mask = (
                    filtered_transactions["sample_code"].fillna("").str.contains(keyword, case=False)
                    | filtered_transactions["sample_name"].fillna("").str.contains(keyword, case=False)
                    | filtered_transactions["remark"].fillna("").str.contains(keyword, case=False)
                )
                filtered_transactions = filtered_transactions[mask]

            if selected_action != "全部":
                filtered_transactions = filtered_transactions[
                    filtered_transactions["action_type"] == selected_action
                ]

            metric_col1, metric_col2 = st.columns(2)
            metric_col1.metric("流水记录数", len(filtered_transactions))
            metric_col2.metric("涉及动作类型", filtered_transactions["action_type"].nunique())
            safe_dataframe(st, filtered_transactions, width="stretch")

