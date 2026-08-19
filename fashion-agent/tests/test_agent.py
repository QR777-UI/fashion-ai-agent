# -*- coding: utf-8 -*-
"""
tests/test_agent.py —— 服装 Agent 自动化测试（pytest）
====================================================
原则：不调用真实 API（mock 掉），测试不花钱、不依赖网络、可随时跑。

运行：cd fashion-agent && python -m pytest tests/ -v
"""

import json
import os
import sys
import types
from unittest.mock import patch, MagicMock

import pytest

from src.agent import planner

# 合法的规划器输出（Pydantic 校验通过）
合法计划 = json.dumps({
    "task_description": "测试任务",
    "steps": [
        {"step_number": 1, "tool": "get_sales", "params": {"category": "外套"}, "purpose": "查销售额"}
    ],
}, ensure_ascii=False)

非法计划 = json.dumps({"task_description": "缺 steps 字段"})


def _mock_chat(content: str):
    """构造一个 fake 的 chat.completions.create 返回值"""
    m = MagicMock()
    m.choices = [MagicMock()]
    m.choices[0].message.content = content
    return m


# ============ 数据加载 ============
def test_load_data_default():
    品类 = planner.load_data()
    assert len(品类) >= 3
    assert "外套" in 品类


def test_load_data_missing_file():
    with pytest.raises(FileNotFoundError):
        planner.load_data("不存在的文件.csv")


# ============ 工具库 ============
def test_tools_basic():
    planner.load_data()
    assert "销售额" in planner.get_sales("外套")
    assert "退货率" in planner.get_return_rate("外套")
    assert "渠道" in planner.get_channel_compare("外套")
    r = planner.make_chart("外套")
    assert r.startswith("已生成趋势图")
    assert os.path.exists(r.split(": ")[-1])


def test_tools_bad_category():
    planner.load_data()
    with pytest.raises(ValueError):
        planner.get_sales("不存在的品类")


# ============ 规划器（mock API） ============
def test_planner_ok():
    planner.load_data()
    with patch.object(planner.client.chat.completions, "create", return_value=_mock_chat(合法计划)):
        plan = planner.规划任务("测试")
    assert len(plan.steps) == 1
    assert plan.steps[0].tool == "get_sales"


def test_planner_retry_success():
    """前 2 次输出非法，第 3 次成功 → 触发重试机制"""
    planner.load_data()
    with patch.object(planner.client.chat.completions, "create",
                      side_effect=[_mock_chat(非法计划), _mock_chat(非法计划), _mock_chat(合法计划)]):
        plan = planner.规划任务("测试")
    assert len(plan.steps) == 1


def test_planner_fail_after_retries():
    """全部输出非法 → 抛 RuntimeError"""
    planner.load_data()
    with patch.object(planner.client.chat.completions, "create", return_value=_mock_chat(非法计划)):
        with pytest.raises(RuntimeError):
            planner.规划任务("测试", max_retry=2)


# ============ 执行器容错 ============
def test_executor_bad_param():
    """AI 传错品类不崩溃，返回执行失败提示"""
    planner.load_data()
    step = planner.任务步骤(step_number=1, tool="get_sales", params={"category": "不存在的品类"}, purpose="x")
    r = planner.执行步骤(step)
    assert "执行失败" in r


# ============ 趋势预测 ============
def test_predict_trend_ok():
    planner.load_data()
    r = planner.predict_trend("外套", 30)
    assert "预测" in r
    assert "件" in r
    assert ("趋势" in r) or ("外推" in r) or ("参考值" in r)


def test_predict_trend_bad_category():
    planner.load_data()
    with pytest.raises(ValueError):
        planner.predict_trend("不存在的品类")


# ============ 联网搜索 ============
def test_search_web_registered():
    assert "search_web" in planner.工具表


def test_search_knowledge_registered():
    assert "search_knowledge" in planner.工具表


def test_search_knowledge_uses_rag(monkeypatch):
    """主 Agent 调用的是 RAG 的纯检索接口，不额外调用一次大模型回答。"""
    fake_module = types.ModuleType("src.rag.vector_rag")
    fake_module.检索知识 = lambda query, top_k=3: f"命中:{query};top_k={top_k}"
    monkeypatch.setitem(sys.modules, "src.rag.vector_rag", fake_module)
    result = planner.search_knowledge("外套趋势", top_k=2)
    assert result == "命中:外套趋势;top_k=2"


def test_search_knowledge_failure(monkeypatch):
    fake_module = types.ModuleType("src.rag.vector_rag")
    def fail(*args, **kwargs):
        raise RuntimeError("模拟向量库异常")
    fake_module.检索知识 = fail
    monkeypatch.setitem(sys.modules, "src.rag.vector_rag", fake_module)
    assert "知识库检索失败" in planner.search_knowledge("外套趋势")


def test_search_web_network_error(monkeypatch):
    """模拟断网：ddgs 抛异常 → 返回失败提示（不依赖真实网络）"""
    class FakeDDGS:
        def __enter__(self):
            raise RuntimeError("模拟断网")
        def __exit__(self, *a):
            pass
    monkeypatch.setattr("ddgs.DDGS", FakeDDGS)
    r = planner.search_web("测试关键词")
    assert "失败" in r


# ============ 调度器全流程（mock） ============
def test_dispatch_mock():
    """完整工作流：规划(mock) → 执行(真实工具) → 汇总(mock) → 保存"""
    planner.load_data()
    fake_calls = {"n": 0}

    def fake_create(**kwargs):
        fake_calls["n"] += 1
        if fake_calls["n"] == 1:
            return _mock_chat(合法计划)          # 第 1 次 = 规划
        return _mock_chat("这是一份测试汇总报告。")  # 第 2 次 = 汇总

    with patch.object(planner.client.chat.completions, "create", side_effect=fake_create):
        result = planner.任务调度("测试", 报告文件名=os.path.join("data", "测试报告.txt"))
    assert "计划" in result
    assert "执行明细" in result
    assert "报告" in result and result["报告"].strip()
    assert "保存结果" in result
