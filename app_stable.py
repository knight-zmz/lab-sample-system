#主入口 app_stable.py，负责：页面导航，加载页面
import streamlit as st

from views import borrow_sample
from views import io_records
from views import project_manage
from views import return_sample
from views import sample_add
from views import sample_out
from views import sample_view

st.set_page_config(
    page_title="实验室样本管理系统",
    layout="wide"
)

st.markdown(
    """
    <style>
    :root {
        --page-bg: linear-gradient(135deg, #f4efe6 0%, #dce8e1 45%, #c6d7d2 100%);
        --panel-bg: rgba(255, 252, 246, 0.82);
        --panel-border: rgba(54, 78, 70, 0.16);
        --accent: #20443c;
        --accent-soft: #6d8d83;
        --text-main: #18302c;
    }

    .stApp {
        background: var(--page-bg);
    }

    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #17322e 0%, #274843 100%);
    }

    [data-testid="stSidebar"] * {
        color: #f4f1e8;
    }

    .hero-card {
        padding: 1.4rem 1.6rem;
        border-radius: 22px;
        background: linear-gradient(120deg, rgba(255, 250, 242, 0.95), rgba(226, 237, 232, 0.9));
        border: 1px solid rgba(32, 68, 60, 0.14);
        box-shadow: 0 18px 50px rgba(31, 49, 44, 0.12);
        margin-bottom: 1rem;
    }

    .hero-card h1 {
        margin: 0;
        color: var(--text-main);
        font-size: 2.2rem;
        letter-spacing: 0.02em;
    }

    .hero-card p {
        margin: 0.6rem 0 0;
        color: #38544d;
        font-size: 1rem;
        max-width: 820px;
    }

    [data-testid="stMetric"] {
        background: var(--panel-bg);
        border: 1px solid var(--panel-border);
        border-radius: 16px;
        padding: 0.6rem 0.8rem;
    }

    [data-testid="stDataFrame"], div[data-baseweb="select"], .stTextInput, .stDateInput, .stTimeInput, .stTextArea {
        border-radius: 14px;
    }

    .stButton > button {
        background: linear-gradient(135deg, #1e4a41, #55776d);
        color: #fbf9f4;
        border: none;
        border-radius: 999px;
        padding: 0.58rem 1.2rem;
        font-weight: 600;
    }
    </style>
    """,
    unsafe_allow_html=True
)

st.markdown(
    """
    <section class="hero-card">
        <h1>实验室样本管理系统</h1>
        <p>以 MySQL 存储过程、视图和业务约束为中心的客户端界面。样本登记、借用、归还、移位、废弃和项目管理在这里汇总为一套可直接操作的工作台。</p>
    </section>
    """,
    unsafe_allow_html=True
)

st.sidebar.markdown("### 功能导航")
st.sidebar.caption("界面逻辑已对齐数据库设计，关键业务动作均通过存储过程执行。")

menu = st.sidebar.radio(
    "选择模块",
    [
        "样本总览",
        "样本登记",
        "样本状态处理",
        "记录中心",
        "项目管理",
        "样本借用",
        "样本归还"
    ],
    label_visibility="collapsed"
)

if menu == "样本总览":
    sample_view.run()

elif menu == "样本登记":
    sample_add.run()

elif menu == "样本状态处理":
    sample_out.run()

elif menu == "记录中心":
    io_records.run()

elif menu == "项目管理":
    project_manage.run()

elif menu == "样本借用":
    borrow_sample.run()

elif menu == "样本归还":
    return_sample.run()