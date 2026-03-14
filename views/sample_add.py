import streamlit as st

from db import call_procedure, query_df
from utils.submit_guard import run_submit_guard, show_success_pending_if_any

_SUBMIT_KEY = "sample_add"


def run():
    if show_success_pending_if_any(_SUBMIT_KEY):
        return

    st.subheader("新增样本")
    st.caption("样本登记通过数据库存储过程完成，自动生成样本编号并写入历史流水。")

    types = query_df("SELECT type_id, type_name FROM sample_types")
    locations = query_df("SELECT location_id, location_name FROM storage_locations")
    projects = query_df("SELECT project_id, project_name FROM projects")
    users = query_df("SELECT user_id, real_name FROM users ORDER BY real_name")

    if types.empty or locations.empty:
        st.warning("请先准备样本类型和存储位置基础数据，再执行登记。")
        return

    sample_name = st.text_input("样本名称", placeholder="例如：血清样本 A-01", key="sample_name_input")

    type_dict = dict(zip(types.type_name, types.type_id))
    location_dict = dict(zip(locations.location_name, locations.location_id))
    project_options = {"未关联项目": None}
    project_options.update(dict(zip(projects.project_name, projects.project_id)))
    user_options = {"系统导入/未指定": None}
    user_options.update(dict(zip(users.real_name, users.user_id)))

    form_col1, form_col2 = st.columns(2)
    with form_col1:
        type_name = st.selectbox("样本类型", list(type_dict.keys()), key="sample_type_select")
        location_name = st.selectbox("存储位置", list(location_dict.keys()), key="sample_location_select")
        project_name = st.selectbox("所属项目", list(project_options.keys()), key="sample_project_select")
    with form_col2:
        created_by = st.selectbox("登记人", list(user_options.keys()), key="sample_created_by_select")
        use_collected_date = st.checkbox("填写采集日期", key="sample_use_date_checkbox")
        collected_date = st.date_input("采集日期", key="sample_date_input") if use_collected_date else None
        remark = st.text_area("登记备注", placeholder="例如：项目首批入库", key="sample_remark_textarea")

    if st.button("新增样本", key="sample_submit"):
        if not sample_name.strip():
            st.warning("请填写样本名称。")
        else:

            def do_submit():
                return call_procedure(
                    "sp_register_sample",
                    (
                        sample_name.strip(),
                        type_dict[type_name],
                        project_options[project_name],
                        location_dict[location_name],
                        collected_date,
                        user_options[created_by],
                        remark.strip() or None,
                    ),
                )

            run_submit_guard(
                _SUBMIT_KEY,
                success_message="✓ 样本登记成功！数据库已自动生成样本编号，并写入 CREATE 历史流水。",
                error_message="✗ 样本登记失败：{msg}",
                run_callback=do_submit,
            )