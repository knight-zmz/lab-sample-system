import streamlit as st
from db import query_df, execute


def run():

    st.subheader("样本借用")

    samples = query_df(
        "SELECT sample_id, sample_name FROM samples WHERE status='in_storage'"
    )

    users = query_df(
        "SELECT user_id, real_name FROM users"
    )

    if samples.empty:
        st.info("当前没有可借用的在库样本。")
        return

    if users.empty:
        st.info("当前没有可选择的借用人。")
        return

    sample_dict = dict(zip(samples.sample_name, samples.sample_id))
    user_dict = dict(zip(users.real_name, users.user_id))

    sample = st.selectbox("选择样本", list(sample_dict.keys()))
    user = st.selectbox("借用人", list(user_dict.keys()))

    return_time = st.date_input("预计归还时间")

    if st.button("登记借用"):

        sql = """
        INSERT INTO borrow_records
        (sample_id, user_id, expected_return_time)
        VALUES (%s,%s,%s)
        """

        execute(
            sql,
            (
                sample_dict[sample],
                user_dict[user],
                return_time
            )
        )

        st.success("借用登记成功")
        