#主入口 app_stable.py，负责：页面导航，加载页面
import streamlit as st

from views import sample_view
from views import sample_add
from views import sample_out
from views import io_records
from views import project_manage
from views import borrow_sample
from views import return_sample

st.set_page_config(
    page_title="实验室样本管理系统",
    layout="wide"
)

st.title("实验室样本管理系统")

menu = st.sidebar.radio(
    "功能菜单",
    [
        "样本信息查看",
        "新增样本",
        "样本出库",
        "出入库记录",
        "项目管理",
        "样本借用",
        "样本归还"
    ]
)

if menu == "样本信息查看":
    sample_view.run()

elif menu == "新增样本":
    sample_add.run()

elif menu == "样本出库":
    sample_out.run()

elif menu == "出入库记录":
    io_records.run()

elif menu == "项目管理":
    project_manage.run()

elif menu == "样本借用":
    borrow_sample.run()

elif menu == "样本归还":
    return_sample.run()