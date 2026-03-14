import streamlit as st

from db import call_procedure, query_df
from utils.submit_guard import run_submit_guard, show_success_pending_if_any

_KEY_MOVE = "sample_out_move"
_KEY_DISPOSE = "sample_out_dispose"


def run():
    if show_success_pending_if_any(_KEY_MOVE):
        return
    if show_success_pending_if_any(_KEY_DISPOSE):
        return

    st.subheader("样本出库与状态处理")
    st.caption("根据数据库设计，这里将原“出库”拆成两类明确动作：库内移位和样本废弃。")

    samples = query_df(
        """
        SELECT sample_id, sample_code, sample_name, type_name, project_name, location_name, status
        FROM v_sample_detail
        ORDER BY created_at DESC, sample_id DESC
        """
    )
    users = query_df("SELECT user_id, real_name FROM users ORDER BY real_name")
    locations = query_df("SELECT location_id, location_name FROM storage_locations ORDER BY location_name")

    if samples.empty:
        st.info("当前没有样本数据。")
        return

    user_options = {"未指定操作人": None}
    user_options.update(dict(zip(users.real_name, users.user_id)))

    available_samples = samples[samples["status"] == "available"]
    move_tab, dispose_tab = st.tabs(["样本移位", "样本废弃"])

    with move_tab:
        st.markdown("仅允许对当前处于 available 状态的样本执行移位。")
        if available_samples.empty or locations.empty:
            st.info("缺少可移位样本或存储位置数据。")
        else:
            move_options = {
                f"{row.sample_code} | {row.sample_name} | 当前位置：{row.location_name}": row.sample_id
                for row in available_samples.itertuples(index=False)
            }
            location_options = dict(zip(locations.location_name, locations.location_id))

            selected_sample = st.selectbox("选择待移位样本", list(move_options.keys()), key="move_sample")
            selected_location = st.selectbox("新存储位置", list(location_options.keys()), key="move_location")
            selected_user = st.selectbox("操作人", list(user_options.keys()), key="move_user")
            move_note = st.text_area("移位备注", placeholder="例如：转存至 B 区 3 层", key="move_note")

            if st.button("执行移位", key="move_submit"):

                def do_submit():
                    return call_procedure(
                        "sp_move_sample",
                        (
                            move_options[selected_sample],
                            location_options[selected_location],
                            user_options[selected_user],
                            move_note.strip() or None,
                        ),
                    )

                run_submit_guard(
                    _KEY_MOVE,
                    success_message="✓ 样本移位成功！MOVE 历史流水已写入数据库。",
                    error_message="✗ 样本移位失败：{msg}",
                    run_callback=do_submit,
                )

    with dispose_tab:
        st.markdown("废弃是终止性状态，只允许对当前处于 available 状态的样本执行。")
        if available_samples.empty:
            st.info("当前没有可废弃的样本。")
        else:
            dispose_options = {
                f"{row.sample_code} | {row.sample_name} | 位置：{row.location_name}": row.sample_id
                for row in available_samples.itertuples(index=False)
            }
            selected_sample = st.selectbox("选择待废弃样本", list(dispose_options.keys()), key="dispose_sample")
            selected_user = st.selectbox("操作人", list(user_options.keys()), key="dispose_user")
            dispose_note = st.text_area("废弃说明", placeholder="例如：污染失效，按流程废弃", key="dispose_note")

            if st.button("执行废弃", key="dispose_submit"):

                def do_submit():
                    return call_procedure(
                        "sp_dispose_sample",
                        (
                            dispose_options[selected_sample],
                            user_options[selected_user],
                            dispose_note.strip() or None,
                        ),
                    )

                run_submit_guard(
                    _KEY_DISPOSE,
                    success_message="✓ 样本废弃成功！状态已更新为 disposed，DISPOSE 历史流水已写入。",
                    error_message="✗ 样本废弃失败：{msg}",
                    run_callback=do_submit,
                )

