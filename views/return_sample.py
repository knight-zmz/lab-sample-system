import streamlit as st

from auth import get_current_user
from db import call_procedure, query_df
from permissions import require_permission
from utils.streamlit_compat import safe_dataframe
from utils.submit_guard import run_submit_guard, show_success_pending_if_any

_SUBMIT_KEY = "return_sample"


def run():
    if not require_permission("sample.write", "当前角色无权执行样本归还。"):
        return

    if show_success_pending_if_any(_SUBMIT_KEY):
        return

    st.subheader("样本归还")
    st.caption("归还通过应用层事务闭环处理，自动更新借用单据、样本状态和历史流水。")
    current_user = get_current_user()

    df = query_df(
        """
        SELECT
            borrow_id,
            sample_id,
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

    if df.empty:
        st.info("当前没有处于借用状态的样本。")
        return

    safe_dataframe(st, df, width="stretch")

    borrow_options = {
        f"借用单 {row.borrow_id} | {row.sample_code} | {row.sample_name} | {row.borrower_name}": row.sample_id
        for row in df.itertuples(index=False)
    }

    sample_label = st.selectbox(
        "选择借用记录",
        list(borrow_options.keys()),
        key="return_borrow_select"
    )

    note = st.text_area("归还备注", placeholder="例如：样本完整归还，状态正常", key="return_note_textarea")

    if st.button("确认归还", key="return_submit"):

        def do_submit():
            return call_procedure(
                "sp_return_sample",
                (
                    borrow_options[sample_label],
                    current_user["user_id"] if current_user else None,
                    note.strip() or None,
                ),
            )

        run_submit_guard(
            _SUBMIT_KEY,
            success_message="✓ 归还成功！样本状态已恢复为 available，RETURN 历史流水已写入。",
            error_message="✗ 归还失败：{msg}",
            run_callback=do_submit,
        )