import streamlit as st

from db import call_procedure, query_df
from utils.submit_guard import run_submit_guard, show_success_pending_if_any

_SUBMIT_KEY = "return_sample"


def run():
    if show_success_pending_if_any(_SUBMIT_KEY):
        return

    st.subheader("样本归还")
    st.caption("归还通过数据库存储过程闭环处理，自动更新借用单据、样本状态和历史流水。")

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

    st.dataframe(df, width="stretch")

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
                    None,
                    note.strip() or None,
                ),
            )

        run_submit_guard(
            _SUBMIT_KEY,
            success_message="✓ 归还成功！样本状态已恢复为 available，RETURN 历史流水已写入。",
            error_message="✗ 归还失败：{msg}",
            run_callback=do_submit,
        )