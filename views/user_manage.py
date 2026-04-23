import streamlit as st

from audit import log_event
from auth import build_password_hash, get_current_user
from db import execute_action, query_df
from permissions import require_permission
from utils.streamlit_compat import safe_dataframe
from utils.submit_guard import run_submit_guard, show_success_pending_if_any

_KEY_CREATE = "user_create"
_KEY_RESET = "user_reset"
_KEY_TOGGLE = "user_toggle"


def run():
    if not require_permission("user.manage", "仅管理员可管理用户。"):
        return

    if show_success_pending_if_any(_KEY_CREATE):
        return
    if show_success_pending_if_any(_KEY_RESET):
        return
    if show_success_pending_if_any(_KEY_TOGGLE):
        return

    st.subheader("用户管理")

    users_df = query_df(
        """
        SELECT user_id, username, real_name, role, is_active, created_at
        FROM users
        ORDER BY created_at DESC, user_id DESC
        """
    )
    safe_dataframe(st, users_df, width="stretch")

    create_tab, edit_tab = st.tabs(["新增用户", "维护用户"])
    actor = get_current_user()

    with create_tab:
        with st.form("create_user_form"):
            username = st.text_input("用户名")
            real_name = st.text_input("姓名")
            role = st.selectbox("角色", ["admin", "staff", "viewer"])
            password = st.text_input("初始密码", type="password")
            submitted = st.form_submit_button("创建用户")

        if submitted:
            if not username.strip() or not real_name.strip() or not password:
                st.warning("请完整填写用户名、姓名和初始密码。")
            else:
                password_hash = build_password_hash(password)

                def do_submit():
                    ok, msg = execute_action(
                        """
                        INSERT INTO users (username, real_name, role, password_hash, is_active)
                        VALUES (?, ?, ?, ?, 1)
                        """,
                        (username.strip().lower(), real_name.strip(), role, password_hash),
                    )
                    if ok:
                        log_event(
                            "user_admin",
                            "create_user",
                            "success",
                            detail=f"创建用户: {username.strip().lower()}",
                            actor_user_id=actor["user_id"],
                            actor_username=actor["username"],
                            target_type="user",
                            target_id=username.strip().lower(),
                        )
                    return ok, msg

                run_submit_guard(
                    _KEY_CREATE,
                    success_message="✓ 用户创建成功。",
                    error_message="✗ 用户创建失败：{msg}",
                    run_callback=do_submit,
                )

    with edit_tab:
        if users_df.empty:
            st.info("当前没有可维护用户。")
            return

        user_options = {
            f"{row.username} | {row.real_name} | {row.role}": row.user_id for row in users_df.itertuples(index=False)
        }
        selected = st.selectbox("选择用户", list(user_options.keys()))
        selected_id = int(user_options[selected])
        selected_row = users_df[users_df["user_id"] == selected_id].iloc[0]

        new_password = st.text_input("重置密码（留空表示不重置）", type="password")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("重置密码", key="user_reset_password"):
                if not new_password:
                    st.warning("请输入新密码。")
                else:
                    password_hash = build_password_hash(new_password)

                    def do_submit():
                        ok, msg = execute_action(
                            "UPDATE users SET password_hash = ? WHERE user_id = ?",
                            (password_hash, selected_id),
                        )
                        if ok:
                            log_event(
                                "user_admin",
                                "reset_password",
                                "success",
                                detail=f"重置密码: {selected_row['username']}",
                                actor_user_id=actor["user_id"],
                                actor_username=actor["username"],
                                target_type="user",
                                target_id=str(selected_id),
                            )
                        return ok, msg

                    run_submit_guard(
                        _KEY_RESET,
                        success_message="✓ 密码重置成功。",
                        error_message="✗ 密码重置失败：{msg}",
                        run_callback=do_submit,
                    )
        with col2:
            current_active = int(selected_row["is_active"])
            toggle_label = "禁用用户" if current_active == 1 else "启用用户"
            if st.button(toggle_label, key="user_toggle_active"):
                target_active = 0 if current_active == 1 else 1

                def do_submit():
                    ok, msg = execute_action(
                        "UPDATE users SET is_active = ? WHERE user_id = ?",
                        (target_active, selected_id),
                    )
                    if ok:
                        log_event(
                            "user_admin",
                            "toggle_active",
                            "success",
                            detail=f"{toggle_label}: {selected_row['username']}",
                            actor_user_id=actor["user_id"],
                            actor_username=actor["username"],
                            target_type="user",
                            target_id=str(selected_id),
                        )
                    return ok, msg

                run_submit_guard(
                    _KEY_TOGGLE,
                    success_message=f"✓ {toggle_label}成功。",
                    error_message="✗ 操作失败：{msg}",
                    run_callback=do_submit,
                )
