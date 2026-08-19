# -*- coding: utf-8 -*-
"""
src/agent/planner.py —— Agent 核心：多步工作流（任务规划器）
============================================================
让 AI 学会"先规划、再执行"：把用户的大任务拆成小步骤，程序按步骤逐步执行。

三种角色：
  规划器 (Planner)  = AI：把任务拆成步骤清单（JSON 结构化输出）
  执行器 (Executor) = 程序：按清单一步步调用本地工具，显示进度
  调度器 (Dispatcher)= 总指挥：规划 → 执行 → 汇总 → 保存报告

工程化改造（2026-08-15）：
  1. 数据加载函数化 load_data()——支持界面传"客户自己的数据"（③数据接入）
  2. 路径/密钥全部走 config.py，不再硬编码
"""

import json
import logging
import os
import time
from typing import Literal, List
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from openai import OpenAI
from pydantic import BaseModel, Field

import config
from src.data.ingestion import load_enterprise_data
from src.evaluation.evaluator import evaluate_run, save_evaluation
from src.observability.trace import finish_run, new_run, save_trace, utc_now

# 日志（行车记录仪）：分级记录，出问题能查"哪一步挂了"
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("fashion-agent")

client = OpenAI(
    api_key=config.DEEPSEEK_API_KEY,
    base_url=config.DEEPSEEK_BASE_URL,
)

plt.rcParams['font.sans-serif'] = ['Microsoft YaHei']
plt.rcParams['axes.unicode_minus'] = False

# ============================================================
# 数据准备（③数据接入：支持切换数据源）
# ============================================================
df = None
可用品类 = []
当前数据源 = None

def load_data(path: str = None, column_mapping: dict[str, str] = None) -> list:
    """加载数据文件，返回可用品类列表。
    支持 CSV / Excel，列名要求：日期、品类、销售额、销量、退货量、渠道"""
    global df, 可用品类, 当前数据源
    path = path or config.DATA_FILE
    if not os.path.exists(path):
        logger.error(f"数据文件不存在：{path}")
        raise FileNotFoundError(f"数据文件不存在：{path}（请上传数据或在 config.py 配置 DATA_FILE）")
    df, source = load_enterprise_data(path, column_mapping=column_mapping)
    当前数据源 = source.to_dict()
    可用品类 = df['品类'].unique().tolist()
    logger.info(f"数据加载成功：{os.path.basename(path)}，品类 {len(可用品类)} 个：{'、'.join(可用品类)}")
    return 可用品类

os.makedirs(config.CHART_DIR, exist_ok=True)

# ============================================================
# ① 工具库（本地技能）—— AI 规划后，程序执行的"手"
# ============================================================
def _check(category: str):
    if category not in 可用品类:
        raise ValueError(f"没有'{category}'这个品类，可用品类：{可用品类}")

def get_sales(category: str) -> str:
    _check(category)
    data = df[df['品类'] == category]
    return f"{category}总销售额: ¥{data['销售额'].sum():,}"

def get_return_rate(category: str) -> str:
    _check(category)
    data = df[df['品类'] == category]
    rate = data['退货量'].sum() / data['销量'].sum() * 100
    return f"{category}退货率: {rate:.1f}% (退货{data['退货量'].sum()}件/总销{data['销量'].sum()}件)"

def get_channel_compare(category: str) -> str:
    _check(category)
    data = df[df['品类'] == category]
    channels = data.groupby('渠道')['销售额'].sum()
    return f"{category}渠道分布:\n" + channels.to_string()

def make_chart(category: str) -> str:
    _check(category)
    data = df[df['品类'] == category].groupby('日期')['销量'].sum()
    plt.figure(figsize=(6, 3.5))
    plt.plot(data.index, data.values, marker='o', linewidth=1.5)
    plt.title(f"{category} 销量趋势")
    plt.xlabel("日期"); plt.ylabel("销量")
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    path = os.path.join(config.CHART_DIR, f"趋势_{category}.png")
    plt.savefig(path, dpi=100)
    plt.close()
    return f"已生成趋势图: {path}"

def save_report(文件名: str, 内容: str) -> str:
    directory = os.path.dirname(os.path.abspath(文件名))
    os.makedirs(directory, exist_ok=True)
    with open(文件名, 'w', encoding='utf-8') as f:
        f.write(内容)
    return f"报告已保存: {文件名}"

def predict_trend(category: str, days: int = 30) -> str:
    """预测品类未来销量趋势（简单版：移动平均 + 线性外推）
    数据足够（≥7天）：最近 30 天线性拟合外推；数据有限（3-6天）：按近 3 日均值常数外推（参考值）"""
    _check(category)
    data = df[df['品类'] == category].groupby('日期')['销量'].sum().sort_index()
    n = len(data)
    if n < 3:
        return f"{category}历史数据不足（仅 {n} 天），无法预测"
    if n >= 7:
        recent = data.tail(30)
        x = np.arange(len(recent))
        slope, intercept = np.polyfit(x, recent.values, 1)   # 线性拟合（斜率=日增/减量）
        forecast = [max(0.0, slope * (len(recent) + i) + intercept) for i in range(1, days + 1)]
        方法 = f"基于近 {len(recent)} 天销量线性趋势外推"
    else:
        base = float(data.tail(3).mean())                    # 数据有限：按近 3 日均量外推
        forecast = [max(0.0, base)] * days
        方法 = f"历史数据有限（仅 {n} 天），按近 3 日均量 {base:.0f} 件常数外推（参考值）"
    total = sum(forecast)
    daily_avg = total / days
    last_avg = float(data.tail(3).mean())
    change = (daily_avg - last_avg) / last_avg * 100 if last_avg > 0 else 0
    trend = "上涨" if change > 5 else ("下跌" if change < -5 else "平稳")
    return (f"{category}未来{days}天预测：预计总销量约 {total:.0f} 件（日均 {daily_avg:.0f} 件），"
            f"较近 3 日均量{trend}（变化 {change:+.1f}%）。{方法}。")

def search_web(keyword: str, max_results: int = 5) -> str:
    """联网搜索（DuckDuckGo 免费，无需 key）：搜索行业趋势/热点，返回标题+摘要
    供 AI 结合本地数据分析，让报告带上真实市场动态"""
    try:
        from ddgs import DDGS
        with DDGS() as ddgs:
            results = list(ddgs.text(keyword, max_results=max_results))
        if not results:
            return f"未搜索到「{keyword}」相关结果"
        lines = []
        for i, r in enumerate(results[:max_results], 1):
            title = r.get("title", "").strip()
            body = r.get("body", "").strip()
            href = r.get("href", "").strip()
            lines.append(f"{i}. {title}\n   {body}\n   {href}")
        logger.info(f"联网搜索「{keyword}」：返回 {len(results)} 条")
        return "\n".join(lines)
    except Exception as e:
        logger.warning(f"联网搜索失败：{e}")
        return f"联网搜索失败：{e}（请检查网络后重试）"


def search_knowledge(query: str, top_k: int = 3) -> str:
    """检索本地服装知识库，返回相关原文片段供最终报告引用。

    使用延迟导入，避免没有执行 RAG 任务时就初始化向量数据库和嵌入模型。
    """
    try:
        from src.rag.vector_rag import 检索知识
        result = 检索知识(query, top_k=top_k)
        logger.info(f"知识库检索「{query}」：top_k={top_k}")
        return result
    except Exception as e:
        logger.warning(f"知识库检索失败：{e}")
        return f"知识库检索失败：{e}（本次报告将仅依据销售数据和其他可用资料）"

# 工具注册表：规划器认识名字，执行器找到函数
工具表 = {
    "get_sales": get_sales,
    "get_return_rate": get_return_rate,
    "get_channel_compare": get_channel_compare,
    "make_chart": make_chart,
    "predict_trend": predict_trend,
    "search_knowledge": search_knowledge,
    "search_web": search_web,
    "save_report": save_report,
}

# 工具说明（给规划器 AI 看）
def 工具说明() -> str:
    return f"""可用工具：
- get_sales({{"category": "外套"}})          查品类总销售额
- get_return_rate({{"category": "外套"}})    查品类退货率
- get_channel_compare({{"category": "外套"}}) 查品类各渠道销售额对比
- make_chart({{"category": "外套"}})         生成品类销量趋势图
- predict_trend({{"category": "外套", "days": 30}})  预测品类未来销量趋势（数值外推）
- search_knowledge({{"query": "2026 秋季男装外套趋势", "top_k": 3}})  检索本地服装趋势/面料/品类知识库
- search_web({{"keyword": "2026 男装趋势", "max_results": 5}})  联网搜索行业热点/趋势（供结合分析）
- save_report({{"文件名": "报告.txt", "内容": "..."}})  保存最终报告
可用品类：{可用品类}"""

# ============================================================
# ② 数据结构契约（复用 Lv1 的结构化输出思路）
# ============================================================
class 任务步骤(BaseModel):
    step_number: int = Field(description="步骤序号，从1开始")
    tool: Literal["get_sales", "get_return_rate", "get_channel_compare", "make_chart", "predict_trend", "search_knowledge", "search_web", "save_report"]
    params: dict = Field(description="工具需要的参数，如 {'category': '外套'}")
    purpose: str = Field(description="这一步想得到什么")

class 任务计划(BaseModel):
    task_description: str = Field(description="用一句话复述用户的任务")
    steps: List[任务步骤] = Field(description="按顺序执行的步骤清单")

def 规划提示词() -> str:
    return f"""你是服装数据分析任务的规划师。用户会给你一个任务，你要把任务拆成"一步步可执行的步骤清单"。

{工具说明()}

规则：
1. 每一步只能用一个工具，参数必须正确（品类只能从可用品类里选）
2. 步骤按顺序排列，后面的步骤可以依赖前面的结果
3. 如果任务涉及多个品类，每个品类单独调工具
4. 用户要求结合流行趋势、面料知识、品类知识或知识库时，必须调用 search_knowledge；需要最新外部市场动态时再调用 search_web
5. 趋势结论必须来自 search_knowledge 或 search_web 的执行结果，不能由模型凭空补充
6. 最后一步用 save_report 保存报告（内容字段先用"待汇总"占位，调度器会填写）
7. 只输出 JSON，不要任何多余文字

JSON 格式如下（键名必须完全一致）：
{{
  "task_description": "复述任务",
  "steps": [
    {{"step_number": 1, "tool": "get_sales", "params": {{"category": "外套"}}, "purpose": "查外套销售额"}}
  ]
}}"""

# ============================================================
# ③ 规划器：AI 把任务拆成步骤（结构化输出 + 校验 + 重试）
# ============================================================
def 规划任务(user_task: str, max_retry: int = None) -> 任务计划:
    max_retry = max_retry or config.MAX_RETRY
    logger.info(f"开始规划任务：{user_task[:50]}...")
    messages = [
        {"role": "system", "content": 规划提示词()},
        {"role": "user", "content": f"任务：{user_task}"},
    ]
    for attempt in range(max_retry):
        try:
            res = client.chat.completions.create(
                model=config.MODEL_NAME, messages=messages, temperature=config.TEMPERATURE
            )
            原始 = res.choices[0].message.content.strip()
            if 原始.startswith("```"):
                原始 = 原始.strip("`").strip()
                if 原始.lower().startswith("json"):
                    原始 = 原始[4:].strip()
            data = json.loads(原始)
            plan = 任务计划(**data)
            for step in plan.steps:
                if step.tool not in 工具表:
                    raise ValueError(f"不存在的工具: {step.tool}")
            logger.info(f"规划成功：{len(plan.steps)} 步")
            return plan
        except Exception as e:
            logger.warning(f"规划第 {attempt+1} 次不合格：{e}")
            messages.append({"role": "user", "content": f"计划不合法，错误：{e}\n请重新只输出正确的 JSON 计划。"})
    logger.error(f"规划器连续 {max_retry} 次输出不合格，任务中止：{user_task[:30]}")
    raise RuntimeError(f"规划器连续 {max_retry} 次输出不合格，无法继续")

# ============================================================
# ④ 执行器：程序按步骤执行，逐步收集结果
# ============================================================
def 执行步骤(step: 任务步骤) -> str:
    func = 工具表[step.tool]
    try:
        result = func(**step.params)
        logger.info(f"步骤{step.step_number} {step.tool} 执行成功")
        return result
    except Exception as e:
        logger.warning(f"步骤{step.step_number} {step.tool} 执行失败：{e}")
        return f"执行失败：{e}"

def 执行计划(plan: 任务计划) -> list:
    results = []
    for step in sorted(plan.steps, key=lambda s: s.step_number):
        if step.tool == "save_report":
            result = "（占位步骤：最终报告由调度器汇总后统一保存）"
        else:
            result = 执行步骤(step)
        results.append((step, result))
    return results


def 执行计划详细(plan: 任务计划) -> list[dict]:
    """执行计划并记录每一步输入、输出、耗时与状态，供审计和评测使用。"""
    records = []
    for step in sorted(plan.steps, key=lambda item: item.step_number):
        started_at = utc_now()
        started = time.perf_counter()
        if step.tool == "save_report":
            result = "（占位步骤：最终报告由调度器汇总后统一保存）"
            status = "skipped"
        else:
            result = 执行步骤(step)
            status = "failed" if result.startswith("执行失败：") else "success"
        records.append({
            "step_number": step.step_number,
            "tool": step.tool,
            "params": step.params,
            "purpose": step.purpose,
            "started_at": started_at,
            "duration_ms": round((time.perf_counter() - started) * 1000, 2),
            "status": status,
            "output": result,
            "evidence_refs": ([当前数据源["source_id"]] if 当前数据源 and step.tool in {
                "get_sales", "get_return_rate", "get_channel_compare", "make_chart", "predict_trend"
            } else []),
        })
    return records

# ============================================================
# ⑤ 汇总器：AI 基于所有步骤结果写最终报告
# ============================================================
def 汇总报告(user_task: str, results: list) -> str:
    steps_text = "\n".join(
        f"[步骤{step.step_number}] {step.tool}({step.params}) → {result}"
        for step, result in results
        if step.tool != "save_report"
    )
    res = client.chat.completions.create(
        model=config.MODEL_NAME,
        messages=[
            {"role": "system", "content": (
                "你是服装行业资深数据分析顾问。只能根据各步骤的真实执行结果写报告，"
                "不得虚构销售数字、知识库内容或市场趋势。请区分销售事实、趋势资料和分析推断，"
                "资料不足时明确说明。所有事实和数字必须在句末引用对应的[步骤N]；引用知识库原文时"
                "同时保留[知识库资料N]标记。报告包含：总体结论、数据要点、趋势依据、行动建议。"
            )},
            {"role": "user", "content": f"原始任务：{user_task}\n\n执行结果：\n{steps_text}"},
        ]
    )
    return res.choices[0].message.content.strip()

# ============================================================
# ⑥ 调度器：规划 → 执行 → 汇总 → 保存（对外只暴露这一个函数）
# ============================================================
def 任务调度(user_task: str, 报告文件名: str = None) -> dict:
    报告文件名 = 报告文件名 or config.REPORT_FILE
    trace = new_run(user_task, config.MODEL_NAME, 当前数据源)
    logger.info("=" * 40)
    logger.info(f"任务开始：{user_task[:60]}，run_id={trace['run_id']}")
    try:
        plan = 规划任务(user_task)
        trace["plan"] = plan.model_dump()
        step_records = 执行计划详细(plan)
        trace["steps"] = step_records
        results = [
            (next(step for step in plan.steps if step.step_number == record["step_number"]), record["output"])
            for record in step_records
        ]
        report = 汇总报告(user_task, results)
        saved = save_report(报告文件名, report)
        evaluation = evaluate_run(report, step_records)
        trace["evaluation"] = evaluation
        finish_run(trace, report=report)
        trace_path = save_trace(trace, config.TRACE_DIR)
        evaluation_path = save_evaluation(trace["run_id"], evaluation, config.EVAL_DIR)
        logger.info(f"任务完成：报告已保存 {报告文件名}，审计记录 {trace_path}")
        logger.info("=" * 40)
        return {
            "运行ID": trace["run_id"],
            "计划": plan,
            "执行明细": results,
            "执行记录": step_records,
            "报告": report,
            "保存结果": saved,
            "评测": evaluation,
            "评测文件": evaluation_path,
            "追溯文件": trace_path,
            "数据源": 当前数据源,
        }
    except Exception as exc:
        finish_run(trace, error=str(exc))
        save_trace(trace, config.TRACE_DIR)
        raise
