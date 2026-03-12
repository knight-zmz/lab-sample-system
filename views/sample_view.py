import streamlit as st
from db import query_df


def run():
    st.subheader("样本信息")

    sql = """
    SELECT
        s.sample_id,
        s.sample_name,
        st.type_name,
        sl.location_name,
        p.project_name,
        s.status,
        s.collected_date
    FROM samples s
    LEFT JOIN sample_types st ON s.type_id = st.type_id
    LEFT JOIN storage_locations sl ON s.location_id = sl.location_id
    LEFT JOIN projects p ON s.project_id = p.project_id
    """

    df = query_df(sql)

    # 适配新版 Streamlit：使用 width='stretch' 代替 use_container_width
    st.dataframe(df, width="stretch") 