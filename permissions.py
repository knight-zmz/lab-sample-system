import streamlit as st

from audit import log_event
from auth import get_current_user


ROLE_PERMISSIONS = {
    "admin": {
        "sample.view",
        "sample.write",
        "project.view",
        "project.write",
        "record.view",
        "user.manage",
        "audit.view",
    },
    "staff": {
        "sample.view",
        "sample.write",
        "project.view",
        "record.view",
    },
    "viewer": {
        "sample.view",
        "project.view",
        "record.view",
    },
}


def can(action: str) -> bool:
    user = get_current_user()
    if not user:
        return False
    role = user.get("role")
    return action in ROLE_PERMISSIONS.get(role, set())


def require_permission(action: str, fail_message: str = "无权限执行该操作。") -> bool:
    if can(action):
        return True
    st.warning(fail_message)
    user = get_current_user()
    log_event(
        "permission",
        "deny",
        "denied",
        detail=f"拒绝动作: {action}",
        actor_user_id=user.get("user_id") if user else None,
        actor_username=user.get("username") if user else None,
    )
    return False
