import streamlit as st
from db import query_df, execute


def run():

    st.subheader("样本归还")

    df = query_df(
        """
        SELECT
            borrow_id,
            sample_id
        FROM borrow_records
        WHERE status='borrowed'
        """
    )

    if df.empty:
        st.info("当前没有处于借用状态的样本。")
        return

    borrow_dict = dict(zip(df.borrow_id, df.sample_id))

    borrow_id = st.selectbox(
        "选择借用记录",
        list(borrow_dict.keys())
    )

    if st.button("确认归还"):

        sql = """
        UPDATE borrow_records
        SET
            status='returned',
            actual_return_time=NOW()
        WHERE borrow_id=%s
        """

        execute(sql, (borrow_id,))

        st.success("归还成功")