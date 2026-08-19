# -*- coding: utf-8 -*-
from __future__ import annotations

import hashlib
import json
import os
import uuid
from datetime import datetime, timezone


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def new_run(user_task: str, model: str, data_source: dict | None) -> dict:
    return {
        "schema_version": "1.0",
        "run_id": uuid.uuid4().hex,
        "started_at": utc_now(),
        "finished_at": None,
        "status": "running",
        "task": user_task,
        "model": model,
        "data_source": data_source,
        "plan": None,
        "steps": [],
        "report": None,
        "report_sha256": None,
        "evaluation": None,
        "error": None,
    }


def finish_run(trace: dict, report: str | None = None, error: str | None = None) -> dict:
    trace["finished_at"] = utc_now()
    trace["status"] = "failed" if error else "completed"
    trace["error"] = error
    if report is not None:
        trace["report"] = report
        trace["report_sha256"] = hashlib.sha256(report.encode("utf-8")).hexdigest()
    return trace


def save_trace(trace: dict, directory: str) -> str:
    os.makedirs(directory, exist_ok=True)
    path = os.path.join(directory, f"{trace['run_id']}.json")
    temporary = f"{path}.tmp"
    with open(temporary, "w", encoding="utf-8") as handle:
        json.dump(trace, handle, ensure_ascii=False, indent=2, default=str)
    os.replace(temporary, path)
    return path
