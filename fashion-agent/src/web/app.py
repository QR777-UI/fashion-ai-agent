# -*- coding: utf-8 -*-
"""
src/web/app.py —— Web 界面（Streamlit）
=====================================
功能：
  1. 上传客户自己的数据（CSV / Excel）——③数据接入
  2. 知识库管理（随时添加资料）
  3. AI 规划 → 程序执行 → AI 汇总 的多步工作流
  4. 示例任务一键填充 + 执行历史记录（⑦界面升级）
  5. 常用任务：保存重复性任务，每周点一下自动运行（⑦升级）

启动：cd fashion-agent && streamlit run src/web/app.py
"""

import os
import json
import tempfile
import streamlit as st

from src.agent import planner  # 用模块引用，保证拿到最新的 可用品类
from src.rag import vector_rag  # 知识库（可随时添加资料）

st.set_page_config(page_title="服装趋势分析 Agent", layout="centered")
st.title("🧥 服装趋势分析 Agent")
st.caption("AI 规划 → 程序执行 → AI 汇总 · 多步工作流")

# ============ 常用任务持久化（重启不丢） ============
SAVED_TASKS_FILE = os.path.join("data", "saved_tasks.json")

def load_saved_tasks() -> list:
    if os.path.exists(SAVED_TASKS_FILE):
        with open(SAVED_TASKS_FILE, encoding="utf-8") as f:
            return json.load(f)
    return []

def save_tasks(tasks: list):
    with open(SAVED_TASKS_FILE, "w", encoding="utf-8") as f:
        json.dump(tasks, f, ensure_ascii=False, indent=2)

if "saved_tasks" not in st.session_state:
    st.session_state.saved_tasks = load_saved_tasks()
if "history" not in st.session_state:
    st.session_state.history = []
if "run_requested" not in st.session_state:
    st.session_state.run_requested = False

# ============ 执行任务（抽成函数，按钮和常用任务共用） ============
def run_task(user_task: str, show_process: bool = False):
    result = planner.任务调度(user_task)
    plan = result["计划"]

    # 详细模式才展示过程（客户用简洁模式，调试/讲解才开详细）
    if show_process:
        st.subheader("📋 第 1 步：AI 规划任务")
        st.write(f"**任务理解：** {plan.task_description}")
        st.table([
            {"步骤": s.step_number, "工具": s.tool, "参数": s.params, "目的": s.purpose}
            for s in sorted(plan.steps, key=lambda x: x.step_number)
        ])

        st.subheader("⚙️ 第 2 步：程序逐步执行")
        for step, step_result in result["执行明细"]:
            st.markdown(f"**步骤 {step.step_number}** · `{step.tool}({step.params})`")
            if step.tool == "make_chart" and "趋势_" in step_result:
                chart_path = step_result.split(": ")[-1]
                st.image(chart_path, width=420)
            else:
                st.code(step_result)

    # 报告始终展示（这是客户要的结果）
    st.subheader("📝 分析报告")
    st.markdown(result["报告"])
    st.success(result["保存结果"])

    st.download_button(
        label="下载分析报告 (txt)",
        data=result["报告"],
        file_name=f"分析报告_{len(st.session_state.history)+1}.txt",
        mime="text/plain",
    )

    st.session_state.history.insert(0, {"任务": user_task, "报告": result["报告"]})
    st.session_state.history = st.session_state.history[:5]

# ============ 侧边栏：常用任务（一键运行） ============
st.sidebar.header("📌 常用任务")
if st.session_state.saved_tasks:
    for t in st.session_state.saved_tasks:
        if st.sidebar.button(f"▶ {t['name']}", key=f"saved_{t['name']}", use_container_width=True):
            st.session_state.user_task = t["task"]
            st.session_state.run_requested = True
            st.rerun()
else:
    st.sidebar.caption("还没有常用任务。执行任务后可在下方保存。")

# ============ 侧边栏：知识库管理（可随时更新） ============
st.sidebar.divider()
st.sidebar.header("📚 知识库")
kb_info = vector_rag.获取知识库概况()
st.sidebar.caption(f"当前知识：{kb_info['块数']} 块（库内 {kb_info['库内条数']} 条）")
kb_file = st.sidebar.file_uploader(
    "添加知识资料（txt/md）",
    type=["txt", "md"],
    help="上传后自动切块入库，立即参与检索回答",
)
if kb_file is not None:
    try:
        文本 = kb_file.read().decode("utf-8", errors="ignore")
        n = vector_rag.添加文档(文本)
        st.sidebar.success(f"✅ 已添加 {n} 块知识")
    except Exception as e:
        st.sidebar.error(f"添加失败：{e}")

# ============ 侧边栏：数据源（③数据接入） ============
st.sidebar.divider()
st.sidebar.header("📁 数据源")
uploaded = st.sidebar.file_uploader(
    "上传销售数据（CSV/Excel）",
    type=["csv", "xlsx", "xls"],
    help="列名要求：日期、品类、销售额、销量、退货量、渠道",
)

try:
    if uploaded is not None:
        suffix = os.path.splitext(uploaded.name)[1]
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp.write(uploaded.getbuffer())
            tmp_path = tmp.name
        可用品类 = planner.load_data(tmp_path)
        数据源名 = uploaded.name
        st.sidebar.success(f"已加载 {uploaded.name}")
    else:
        可用品类 = planner.load_data()
        数据源名 = os.path.basename(planner.config.DATA_FILE)
except Exception as e:
    st.sidebar.error(f"数据加载失败：{e}")
    可用品类 = planner.可用品类 or []
    数据源名 = "加载失败"

st.info(f"📊 数据源：{数据源名} ｜ 可用品类：{'、'.join(可用品类)}")

# 展示模式开关：默认简洁（只出报告），开详细才看过程
show_process = st.sidebar.toggle(
    "🔧 显示执行过程（详细模式）",
    value=False,
    help="给企业客户用：关闭（只看报告）。调试/讲解时：打开（看规划步骤）。",
)

# ============ 任务输入 + 示例 + 保存 ============
示例任务 = st.sidebar.selectbox(
    "✨ 示例任务",
    ["（自定义任务）", "分析外套的销售额和退货率", "对比外套和衬衫两个品类的销售表现", "分析裤子的渠道分布"],
)
if 示例任务 != "（自定义任务）":
    st.session_state.user_task = 示例任务

user_task = st.text_area(
    "下达任务",
    value=st.session_state.get("user_task", ""),
    placeholder="例如：分析外套和衬衫两个品类的销售表现，对比退货率，生成趋势图，并保存一份对比报告",
    height=90,
)

col_run, col_save = st.columns([3, 2])
with col_run:
    run_clicked = st.button("🚀 执行任务", type="primary", use_container_width=True)
with col_save:
    save_name = st.text_input("保存为常用任务（输入名字）", placeholder="如：每周一外套销售周报")

if save_name.strip() and user_task.strip():
    # 已存在则覆盖，否则新增
    names = [t["name"] for t in st.session_state.saved_tasks]
    if save_name in names:
        for t in st.session_state.saved_tasks:
            if t["name"] == save_name:
                t["task"] = user_task
    else:
        st.session_state.saved_tasks.append({"name": save_name, "task": user_task})
    save_tasks(st.session_state.saved_tasks)
    st.sidebar.success(f"📌 已保存常用任务「{save_name}」")

# ============ 执行 ============
if run_clicked and user_task.strip():
    st.session_state.run_requested = True

if st.session_state.run_requested and st.session_state.get("user_task", "").strip():
    task_to_run = st.session_state.user_task
    st.session_state.run_requested = False
    with st.spinner("工作流执行中..."):
        run_task(task_to_run, show_process)

# ============ 历史记录（可回看/再下载） ============
if st.session_state.history:
    st.divider()
    st.subheader("🗂️ 本次会话历史")
    for i, item in enumerate(st.session_state.history):
        with st.expander(f"#{i+1} {item['任务'][:40]}"):
            st.markdown(item["报告"])
            st.download_button(
                label=f"下载 #{i+1} 报告",
                data=item["报告"],
                file_name=f"历史报告_{i+1}.txt",
                mime="text/plain",
                key=f"hist_{i}",
            )
