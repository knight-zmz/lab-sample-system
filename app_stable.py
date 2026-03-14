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
        --page-bg: linear-gradient(145deg, #eef5f2 0%, #e2ebe6 35%, #d4e2dc 70%, #c5d9d1 100%);
        --panel-bg: rgba(255, 253, 249, 0.92);
        --panel-border: rgba(40, 72, 64, 0.12);
        --accent: #1a3d36;
        --accent-soft: #5a8578;
        --accent-light: #7a9d92;
        --text-main: #162c28;
        --text-muted: #4a6560;
        --radius: 16px;
        --radius-sm: 12px;
        --shadow: 0 4px 24px rgba(26, 61, 54, 0.08);
        --shadow-hover: 0 8px 32px rgba(26, 61, 54, 0.12);
    }

    .stApp {
        background: var(--page-bg);
        background-attachment: fixed;
    }

    [data-testid="stSidebar"] {
        background: linear-gradient(185deg, #132d28 0%, #1e3d36 50%, #244039 100%);
        box-shadow: 4px 0 24px rgba(0,0,0,0.06);
    }

    [data-testid="stSidebar"] * {
        color: #eef4f1;
    }

    [data-testid="stSidebar"] [data-baseweb="radio"] label {
        border-radius: var(--radius-sm);
        padding: 0.4rem 0.75rem;
        transition: background 0.2s, color 0.2s;
    }

    [data-testid="stSidebar"] [data-baseweb="radio"] label:hover {
        background: rgba(255,255,255,0.08);
    }

    [data-testid="stSidebar"] [data-baseweb="radio"] label[data-checked="true"] {
        background: rgba(255,255,255,0.14);
        color: #fff;
    }

    .hero-card {
        padding: 1.75rem 2rem;
        border-radius: 24px;
        background: linear-gradient(125deg, rgba(255, 252, 248, 0.98), rgba(232, 242, 238, 0.95));
        border: 1px solid rgba(26, 61, 54, 0.1);
        box-shadow: var(--shadow);
        margin-bottom: 1.5rem;
    }

    .hero-card h1 {
        margin: 0;
        color: var(--text-main);
        font-size: 2rem;
        font-weight: 700;
        letter-spacing: 0.02em;
    }

    .hero-card p {
        margin: 0.75rem 0 0;
        color: var(--text-muted);
        font-size: 0.95rem;
        line-height: 1.55;
        max-width: 780px;
    }

    [data-testid="stMetric"] {
        background: var(--panel-bg);
        border: 1px solid var(--panel-border);
        border-radius: var(--radius);
        padding: 0.75rem 1rem;
        box-shadow: var(--shadow);
    }

    [data-testid="stDataFrame"], div[data-baseweb="select"], .stTextInput, .stDateInput, .stTimeInput, .stTextArea {
        border-radius: var(--radius-sm);
    }

    .stButton > button {
        background: linear-gradient(135deg, #1a453c, #4a7266);
        color: #fafcfb;
        border: none;
        border-radius: 999px;
        padding: 0.6rem 1.35rem;
        font-weight: 600;
        box-shadow: 0 2px 12px rgba(26, 69, 60, 0.25);
        transition: transform 0.15s, box-shadow 0.2s, background 0.2s;
    }

    .stButton > button:hover {
        transform: translateY(-1px);
        box-shadow: 0 4px 16px rgba(26, 69, 60, 0.3);
        background: linear-gradient(135deg, #1e4e44, #527a6d);
    }

    .stButton > button:active {
        transform: translateY(0);
    }

    [data-testid="stExpander"] {
        border-radius: var(--radius-sm);
        border: 1px solid var(--panel-border);
        background: var(--panel-bg);
    }

    div[data-baseweb="select"] > div {
        border-radius: var(--radius-sm);
    }

    [data-testid="stSpinner"] {
        margin: 0.5rem 0;
    }

    .stSuccess, .stError, .stWarning {
        border-radius: var(--radius-sm);
        padding: 0.6rem 1rem;
    }
    </style>
    """,
    unsafe_allow_html=True
)

st.markdown(
    """
    <section class="hero-card">
        <h1>实验室样本管理系统</h1>
        <p>基于 MySQL 存储过程与视图的样本全生命周期管理：登记、借用、归还、移位、废弃与项目管理，均在此统一操作。</p>
    </section>
    """,
    unsafe_allow_html=True
)

st.sidebar.markdown("### 功能导航")
st.sidebar.caption("关键操作均通过存储过程执行，数据一致性与约束由数据库保障。")

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