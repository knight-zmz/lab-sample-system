import streamlit as st


def safe_rerun():
    """
    Streamlit 1.10 使用 experimental_rerun，新版本使用 rerun。
    """
    if hasattr(st, "rerun"):
        st.rerun()
        return
    st.experimental_rerun()


def safe_radio(container, label, options):
    """
    兼容旧版 Streamlit 不支持 label_visibility 参数。
    """
    try:
        return container.radio(label, options, label_visibility="collapsed")
    except TypeError:
        return container.radio(label, options)


def safe_dataframe(container, data, width="stretch", **kwargs):
    """
    兼容新版 width='stretch' 与旧版只接受 int/None 的差异。
    """
    try:
        if width == "stretch":
            return container.dataframe(data, use_container_width=True, **kwargs)
        if width is None:
            return container.dataframe(data, **kwargs)
        return container.dataframe(data, width=width, **kwargs)
    except TypeError:
        if width is not None and not isinstance(width, str):
            try:
                return container.dataframe(data, width=width, **kwargs)
            except TypeError:
                pass
        return container.dataframe(data, **kwargs)
