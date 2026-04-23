import hashlib
import hmac

import streamlit as st

from audit import log_event
from db import fetch_one
from db_init import hash_password
from utils.streamlit_compat import safe_rerun


SESSION_USER_KEY = "auth_current_user"


def verify_password(password, stored_hash):
    try:
        scheme, salt, digest = stored_hash.split("$", 2)
    except ValueError:
        return False
    if scheme != "pbkdf2_sha256":
        return False
    computed = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 120000).hex()
    return hmac.compare_digest(computed, digest)


def build_password_hash(password):
    return hash_password(password)


def get_current_user():
    return st.session_state.get(SESSION_USER_KEY)


def is_logged_in():
    return get_current_user() is not None


def login(username, password):
    user = fetch_one(
        """
        SELECT user_id, username, real_name, role, password_hash, is_active
        FROM users
        WHERE username = ?
        """,
        (username.strip().lower(),),
    )
    if not user:
        log_event("auth", "login", "failure", detail=f"用户不存在: {username}", actor_username=username)
        return False, "用户名或密码错误"
    if int(user["is_active"]) != 1:
        log_event("auth", "login", "failure", detail=f"用户已禁用: {user['username']}", actor_username=user["username"])
        return False, "用户已被禁用"
    if not verify_password(password, str(user["password_hash"])):
        log_event("auth", "login", "failure", detail=f"密码错误: {user['username']}", actor_username=user["username"])
        return False, "用户名或密码错误"

    safe_user = {
        "user_id": int(user["user_id"]),
        "username": str(user["username"]),
        "real_name": str(user["real_name"]),
        "role": str(user["role"]),
    }
    st.session_state[SESSION_USER_KEY] = safe_user
    log_event("auth", "login", "success", detail="登录成功", actor_user_id=safe_user["user_id"], actor_username=safe_user["username"])
    return True, None


def logout():
    user = get_current_user()
    if user:
        log_event("auth", "logout", "success", detail="用户退出", actor_user_id=user["user_id"], actor_username=user["username"])
    st.session_state.pop(SESSION_USER_KEY, None)


def render_login_form():
    if is_logged_in():
        return True

    st.title("实验室样本管理系统")
    st.subheader("用户登录")
    with st.form("login_form"):
        username = st.text_input("用户名")
        password = st.text_input("密码", type="password")
        submitted = st.form_submit_button("登录")
    if submitted:
        success, err = login(username, password)
        if success:
            safe_rerun()
        else:
            st.error(err or "登录失败")
    st.info("默认管理员账号请参考 README 初始化说明。")
    return False
