import streamlit as st

from db import call_procedure, query_df


def run():
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
        list(borrow_options.keys())
    )

    note = st.text_area("归还备注", placeholder="例如：样本完整归还，状态正常")

    if st.button("确认归还"):
        success, error_message = call_procedure(
            "sp_return_sample",
            (
                borrow_options[sample_label],
                None,
                note.strip() or None,
            )
        )

        if success:
            st.success("归还成功。样本状态已恢复为 available，并写入 RETURN 历史流水。")
        else:
            st.error(f"归还失败：{error_message}")