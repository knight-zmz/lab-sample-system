import streamlit as st
from db import query_df, execute


def run():
    st.subheader("新增样本")

    types = query_df("SELECT type_id, type_name FROM sample_types")
    locations = query_df("SELECT location_id, location_name FROM storage_locations")
    projects = query_df("SELECT project_id, project_name FROM projects")

    sample_name = st.text_input("样本名称")

    type_dict = dict(zip(types.type_name, types.type_id))
    location_dict = dict(zip(locations.location_name, locations.location_id))
    project_dict = dict(zip(projects.project_name, projects.project_id))

    type_name = st.selectbox("样本类型", list(type_dict.keys()))
    location_name = st.selectbox("存储位置", list(location_dict.keys()))
    project_name = st.selectbox("所属项目", list(project_dict.keys()))

    collected_date = st.date_input("采集日期")

    if st.button("新增样本"):

        sql = """
        INSERT INTO samples
        (sample_name, type_id, location_id, project_id, collected_date)
        VALUES (%s,%s,%s,%s,%s)
        """

        execute(
            sql,
            (
                sample_name,
                type_dict[type_name],
                location_dict[location_name],
                project_dict[project_name],
                collected_date
            )
        )

        st.success("新增成功")