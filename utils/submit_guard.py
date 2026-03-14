"""
防重复提交：通过 session_state 锁 + 成功后的二次 rerun，避免因网络延迟导致同一操作执行两次。
"""
import streamlit as st


def is_submitting(key: str) -> bool:
    """当前是否处于「已点击提交、等待结果」状态（用于在 rerun 后显示“提交成功，正在刷新”）。"""
    return bool(st.session_state.get(key, False))


def set_submitting(key: str, value: bool) -> None:
    st.session_state[key] = value


def set_success_pending(key: str, message: str, error: bool = False) -> None:
    """标记本次提交已完成，下次 run 时只展示结果并刷新（避免重复执行）。"""
    st.session_state[f"_success_pending_{key}"] = message
    st.session_state[f"_success_pending_error_{key}"] = error


def consume_success_pending(key: str) -> tuple[str | None, bool]:
    """取出并清除「待展示的成功/失败信息」，返回 (message, is_error)。"""
    msg = st.session_state.pop(f"_success_pending_{key}", None)
    is_err = st.session_state.pop(f"_success_pending_error_{key}", False)
    return (msg, is_err)


def run_submit_guard(
    key: str,
    success_message: str,
    error_message: str,
    run_callback,
) -> bool:
    """
    在带锁和 spinner 的情况下执行一次提交，并处理成功后的防重复逻辑。
    - 点击后立即加锁，在 spinner 内执行 run_callback()。
    - 成功：设置 success_pending 并 rerun，不在本 run 内清锁，下次 run 展示成功并清锁再 rerun。
    - 失败：本 run 内清锁并展示错误。
    返回：是否执行了提交（True 表示已处理，调用方无需再 st.rerun）。
    """
    if st.session_state.get(key):
        return True  # 已处于提交中，不应再进入（保险）

    st.session_state[key] = True
    success = False
    try:
        with st.spinner("提交中，请勿重复点击…"):
            success, err_msg = run_callback()
        if success:
            set_success_pending(key, success_message, error=False)
            st.rerun()
            return True
        else:
            st.error(error_message.format(msg=err_msg))
            return False
    except Exception as e:
        st.error(f"提交异常：{e}")
        return False
    finally:
        if not success and not st.session_state.get(f"_success_pending_{key}"):
            set_submitting(key, False)


def show_success_pending_if_any(key: str) -> bool:
    """
    若存在待展示的成功/失败信息，则展示并清锁、再 rerun 一次以回到正常表单。
    返回 True 表示已展示并触发了 rerun，调用方应 return；否则返回 False。
    """
    msg, is_error = consume_success_pending(key)
    if msg is None:
        return False
    if is_error:
        st.error(msg)
    else:
        st.success(msg)
    set_submitting(key, False)
    st.rerun()
    return True
