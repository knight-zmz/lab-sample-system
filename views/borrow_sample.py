import time as time_module
from datetime import datetime, time

import streamlit as st

from db import call_procedure, query_df


def run():
    st.subheader("样本借用")
    st.caption("借用登记通过数据库存储过程完成，样本状态和借用单据会同步更新。")

    samples = query_df(
        """
        SELECT sample_id, sample_code, sample_name, type_name, location_name
        FROM v_sample_detail
        WHERE status = 'available'
        ORDER BY created_at DESC, sample_id DESC
        """
    )

    users = query_df(
        "SELECT user_id, real_name FROM users ORDER BY real_name"
    )

    if samples.empty:
        st.info("当前没有可借用的在库样本。")
        return

    if users.empty:
        st.info("当前没有可选择的借用人。")
        return

    sample_labels = {
        f"{row.sample_code} | {row.sample_name} | {row.type_name} | {row.location_name}": row.sample_id
        for row in samples.itertuples(index=False)
    }
    user_dict = dict(zip(users.real_name, users.user_id))

    left_col, right_col = st.columns(2)
    with left_col:
        sample = st.selectbox("选择样本", list(sample_labels.keys()))
        user = st.selectbox("借用人", list(user_dict.keys()))
    with right_col:
        return_date = st.date_input("预计归还日期")
        return_time = st.time_input("预计归还时间", value=time(18, 0))

    purpose = st.text_input("借用用途", placeholder="例如：实验检测、复核分析", key="borrow_purpose_input")
    note = st.text_area("借用备注", placeholder="可填写附加说明", key="borrow_note_textarea")

    if st.button("登记借用", key="borrow_submit"):
        expected_return_at = datetime.combine(return_date, return_time)

        success, error_message = call_procedure(
            "sp_borrow_sample",
            (
                sample_labels[sample],
                user_dict[user],
                expected_return_at,
                purpose.strip() or None,
                note.strip() or None,
            )
        )

        if success:
            st.success("✓ 借用登记成功！样本状态已更新为 borrowed，借用单据和历史流水已写入。")
            time_module.sleep(1.2)
            st.rerun()
        else:
            st.error(f"✗ 借用登记失败：{error_message}")
        