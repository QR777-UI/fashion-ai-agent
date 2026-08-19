# -*- coding: utf-8 -*-
import json

import pandas as pd
import pytest

from src.data.ingestion import load_enterprise_data
from src.evaluation.evaluator import evaluate_run, save_evaluation
from src.observability.trace import finish_run, new_run, save_trace


def test_enterprise_alias_mapping_and_source_fingerprint(tmp_path):
    path = tmp_path / "erp.csv"
    pd.DataFrame([{
        "date": "2026-08-01", "category": "外套", "revenue": 1200,
        "quantity": 10, "returns": 1, "channel": "直营网店",
    }]).to_csv(path, index=False)
    frame, source = load_enterprise_data(str(path))
    assert list(frame.columns) == ["日期", "品类", "销售额", "销量", "退货量", "渠道"]
    assert source.source_id.startswith("data:")
    assert len(source.file_sha256) == 64
    assert source.quality["invalid_rows"] == 0


def test_enterprise_quality_rejects_impossible_returns(tmp_path):
    path = tmp_path / "bad.csv"
    pd.DataFrame([{
        "日期": "2026-08-01", "品类": "外套", "销售额": 100,
        "销量": 1, "退货量": 2, "渠道": "门店",
    }]).to_csv(path, index=False)
    with pytest.raises(ValueError, match="退货量大于销量"):
        load_enterprise_data(str(path))


def test_trace_is_auditable_json(tmp_path):
    trace = new_run("测试", "fake-model", {"source_id": "data:abc"})
    trace["steps"] = [{"tool": "get_sales", "status": "success", "output": "100"}]
    finish_run(trace, report="报告")
    path = save_trace(trace, str(tmp_path))
    saved = json.loads(open(path, encoding="utf-8").read())
    assert saved["status"] == "completed"
    assert saved["report_sha256"]


def test_evaluation_detects_grounded_and_unsupported_numbers(tmp_path):
    steps = [{
        "tool": "get_sales", "status": "success",
        "output": "外套总销售额: ¥1,200", "step_number": 1,
    }]
    report = "# 总体结论\n销售额1200。[步骤1]\n# 数据要点\n同上。\n# 趋势依据\n资料不足。\n# 行动建议\n保持观察。"
    result = evaluate_run(report, steps)
    assert result["metrics"]["execution_success_rate"] == 1.0
    assert result["metrics"]["section_coverage"] == 1.0
    assert "1200" not in result["details"]["unsupported_numbers"]
    saved = save_evaluation("run-1", result, str(tmp_path))
    assert json.loads(open(saved, encoding="utf-8").read())["run_id"] == "run-1"
