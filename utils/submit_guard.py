"""
防重复提交：通过 session_state 锁 + 成功后的二次 rerun，避免因网络延迟导致同一操作执行两次。
提交过程与成功结果均有明显提示，便于用户感知状态。
"""
import html
import time
import streamlit as st


def is_submitting(key: str) -> bool:
    """当前是否处于「已点击提交、等待结果」状态。"""
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


# 提交中：使用 st.status 更醒目（Streamlit 1.28+），否则用 info + spinner
def _run_with_visible_progress(run_callback):
    try:
        with st.status("**正在提交…** 请稍候，请勿关闭或重复点击。", expanded=True) as status:
            st.caption("正在处理您的请求并写入数据库…")
            success, err_msg = run_callback()
            if success:
                status.update(label="提交完成", state="complete")
            return success, err_msg
    except (TypeError, AttributeError):
        # 旧版 Streamlit 或无 status 时回退
        progress_placeholder = st.empty()
        with progress_placeholder.container():
            st.info("**正在提交…** 请稍候，请勿关闭或重复点击。")
        with st.spinner("处理中…"):
            success, err_msg = run_callback()
        progress_placeholder.empty()
        return success, err_msg


def run_submit_guard(
    key: str,
    success_message: str,
    error_message: str,
    run_callback,
) -> bool:
    """
    在带明显进度提示和锁的情况下执行一次提交，并处理成功后的防重复逻辑。
    """
    if st.session_state.get(key):
        return True

    st.session_state[key] = True
    success = False
    try:
        success, err_msg = _run_with_visible_progress(run_callback)
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
    若存在待展示的成功/失败信息，则用醒目方式展示，停留约 2.5 秒后自动刷新回到表单。
    """
    msg, is_error = consume_success_pending(key)
    if msg is None:
        return False

    set_submitting(key, False)

    if is_error:
        st.error(msg)
        st.rerun()
        return True

    # 成功：醒目横幅 + 自动停留后刷新
    safe_msg = html.escape(msg)
    st.markdown(
        f"""
        <div class="submit-success-banner">
            <span class="submit-success-icon">✓</span>
            <div>
                <strong>提交成功</strong>
                <p class="submit-success-detail">{safe_msg}</p>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    time.sleep(2.5)
    st.rerun()
    return True
