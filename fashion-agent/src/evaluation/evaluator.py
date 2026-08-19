# -*- coding: utf-8 -*-
"""无需调用外部模型的可重复评测，适合 CI 和企业验收基线。"""

from __future__ import annotations

import json
import os
import re


REQUIRED_SECTIONS = ("总体结论", "数据要点", "趋势依据", "行动建议")


def evaluate_run(report: str, step_records: list[dict]) -> dict:
    report = report or ""
    executed = [step for step in step_records if step.get("tool") != "save_report"]
    successful = [step for step in executed if step.get("status") == "success"]
    evidence = "\n".join(str(step.get("output", "")) for step in successful)
    normalized_report = report.replace(",", "")
    normalized_evidence = evidence.replace(",", "")
    report_numbers = set(re.findall(r"(?<!步骤)(?<!资料)\d+(?:\.\d+)?%?", normalized_report))
    evidence_numbers = set(re.findall(r"\d+(?:\.\d+)?%?", normalized_evidence))
    unsupported = sorted(report_numbers - evidence_numbers)
    section_hits = [section for section in REQUIRED_SECTIONS if section in report]
    citation_hits = set(re.findall(r"\[(?:步骤|知识库资料)\d+\]", report))
    metrics = {
        "execution_success_rate": round(len(successful) / len(executed), 4) if executed else 1.0,
        "section_coverage": round(len(section_hits) / len(REQUIRED_SECTIONS), 4),
        "citation_coverage": round(min(1.0, len(citation_hits) / len(successful)), 4) if successful else 0.0,
        "numeric_groundedness": round(
            (len(report_numbers) - len(unsupported)) / len(report_numbers), 4
        ) if report_numbers else 1.0,
    }
    score = round(sum(metrics.values()) / len(metrics) * 100, 1)
    return {
        "score": score,
        "passed": score >= 75 and metrics["execution_success_rate"] == 1.0,
        "metrics": metrics,
        "details": {
            "present_sections": section_hits,
            "unsupported_numbers": unsupported,
            "successful_steps": len(successful),
            "executed_steps": len(executed),
        },
    }


def save_evaluation(run_id: str, evaluation: dict, directory: str) -> str:
    os.makedirs(directory, exist_ok=True)
    path = os.path.join(directory, f"{run_id}.json")
    temporary = f"{path}.tmp"
    payload = {"schema_version": "1.0", "run_id": run_id, **evaluation}
    with open(temporary, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
    os.replace(temporary, path)
    return path
