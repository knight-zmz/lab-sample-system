from datetime import date

import streamlit as st

from db import execute_action, query_df
from utils.submit_guard import run_submit_guard, show_success_pending_if_any

_KEY_CREATE = "project_create"
_KEY_UPDATE = "project_update"
_KEY_DELETE = "project_delete"


def run():
    if show_success_pending_if_any(_KEY_CREATE):
        return
    if show_success_pending_if_any(_KEY_UPDATE):
        return
    if show_success_pending_if_any(_KEY_DELETE):
        return

    st.subheader("项目管理")
    st.caption("提供项目主数据查看、统计和维护能力，并与样本项目关联保持一致。")

    projects_df = query_df(
        """
        SELECT
            project_id,
            project_name,
            principal_investigator,
            start_date,
            end_date,
            description
        FROM projects
        ORDER BY project_name
        """
    )
    stats_df = query_df(
        """
        SELECT project_id, project_name, sample_count
        FROM v_project_sample_statistics
        ORDER BY sample_count DESC, project_name
        """
    )

    overview_tab, create_tab, edit_tab = st.tabs(["项目概览", "新增项目", "编辑项目"])

    with overview_tab:
        metric_col1, metric_col2 = st.columns(2)
        metric_col1.metric("项目总数", len(projects_df))
        metric_col2.metric("已关联样本项目数", int((stats_df["sample_count"] > 0).sum()) if not stats_df.empty else 0)

        st.markdown("项目列表")
        if projects_df.empty:
            st.info("当前还没有项目数据。")
        else:
            st.dataframe(projects_df, width="stretch")

        st.markdown("项目样本统计")
        if stats_df.empty:
            st.info("当前没有项目统计数据。")
        else:
            st.dataframe(stats_df, width="stretch")

            selected_project_name = st.selectbox(
                "查看项目关联样本",
                stats_df["project_name"].tolist(),
                key="project_samples_selector"
            )
            samples_df = query_df(
                """
                SELECT sample_id, sample_code, sample_name, type_name, location_name, status, collected_date
                FROM v_sample_detail
                WHERE project_name = %s
                ORDER BY created_at DESC, sample_id DESC
                """,
                (selected_project_name,)
            )

            if samples_df.empty:
                st.info("该项目当前没有关联样本。")
            else:
                st.dataframe(samples_df, width="stretch")

    with create_tab:
        with st.form("create_project_form"):
            project_name = st.text_input("项目名称")
            principal_investigator = st.text_input("项目负责人")
            enable_start = st.checkbox("填写开始日期", value=True)
            start_date = st.date_input("开始日期") if enable_start else None
            enable_end = st.checkbox("填写结束日期")
            end_date = st.date_input("结束日期") if enable_end else None
            description = st.text_area("项目说明")
            submitted = st.form_submit_button("新增项目")

        if submitted:
            if not (project_name or "").strip():
                st.warning("请填写项目名称。")
            elif end_date is not None and start_date is None:
                st.warning("填写结束日期时，请同时填写开始日期。")
            else:

                def do_submit():
                    return execute_action(
                        """
                        INSERT INTO projects (
                            project_name,
                            principal_investigator,
                            start_date,
                            end_date,
                            description
                        ) VALUES (%s, %s, %s, %s, %s)
                        """,
                        (
                            (project_name or "").strip(),
                            (principal_investigator or "").strip() or None,
                            start_date,
                            end_date,
                            (description or "").strip() or None,
                        ),
                    )

                run_submit_guard(
                    _KEY_CREATE,
                    success_message="✓ 项目新增成功！",
                    error_message="✗ 项目新增失败：{msg}",
                    run_callback=do_submit,
                )

    with edit_tab:
        if projects_df.empty:
            st.info("当前没有可编辑的项目。")
            return

        project_options = {
            f"{row.project_name} | 负责人：{row.principal_investigator or '未填写'}": row.project_id
            for row in projects_df.itertuples(index=False)
        }
        selected_label = st.selectbox("选择项目", list(project_options.keys()))
        selected_project = projects_df[projects_df["project_id"] == project_options[selected_label]].iloc[0]

        with st.form("edit_project_form"):
            project_name = st.text_input("项目名称", value=selected_project["project_name"])
            principal_investigator = st.text_input(
                "项目负责人",
                value=selected_project["principal_investigator"] or ""
            )
            has_start = bool(selected_project["start_date"])
            has_end = bool(selected_project["end_date"])
            enable_start = st.checkbox("填写开始日期", value=has_start, key="edit_enable_start")
            start_date = st.date_input(
                "开始日期",
                value=selected_project["start_date"] if has_start else date.today(),
                key="edit_start_date"
            ) if enable_start else None
            enable_end = st.checkbox("填写结束日期", value=has_end, key="edit_enable_end")
            end_date = st.date_input(
                "结束日期",
                value=selected_project["end_date"] if has_end else date.today(),
                key="edit_end_date"
            ) if enable_end else None
            description = st.text_area("项目说明", value=selected_project["description"] or "")

            update_submitted = st.form_submit_button("保存修改")
            delete_submitted = st.form_submit_button("删除项目")

        if update_submitted:
            if not (project_name or "").strip():
                st.warning("请填写项目名称。")
            elif end_date is not None and start_date is None:
                st.warning("填写结束日期时，请同时填写开始日期。")
            else:

                def do_submit():
                    return execute_action(
                        """
                        UPDATE projects
                        SET
                            project_name = %s,
                            principal_investigator = %s,
                            start_date = %s,
                            end_date = %s,
                            description = %s
                        WHERE project_id = %s
                        """,
                        (
                            (project_name or "").strip(),
                            (principal_investigator or "").strip() or None,
                            start_date,
                            end_date,
                        (description or "").strip() or None,
                        int(selected_project["project_id"]),
                    ),
                )

                run_submit_guard(
                    _KEY_UPDATE,
                    success_message="✓ 项目更新成功！",
                    error_message="✗ 项目更新失败：{msg}",
                    run_callback=do_submit,
                )

        if delete_submitted:
            related_sample_count = query_df(
                "SELECT COUNT(*) AS sample_count FROM samples WHERE project_id = %s",
                (int(selected_project["project_id"]),)
            )["sample_count"].iloc[0]

            if related_sample_count > 0:
                st.warning(f"该项目仍关联 {related_sample_count} 个样本，不能直接删除。")
            else:

                def do_submit():
                    return execute_action(
                        "DELETE FROM projects WHERE project_id = %s",
                        (int(selected_project["project_id"]),),
                    )

                run_submit_guard(
                    _KEY_DELETE,
                    success_message="✓ 项目删除成功！",
                    error_message="✗ 项目删除失败：{msg}",
                    run_callback=do_submit,
                )

