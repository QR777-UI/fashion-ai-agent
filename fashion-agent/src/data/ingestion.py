# -*- coding: utf-8 -*-
"""统一的企业销售数据接入层。

把不同系统导出的 CSV/Excel 映射为 Agent 的标准字段，同时生成可审计的
数据源指纹和质量报告。原始文件不会被修改。
"""

from __future__ import annotations

import hashlib
import os
from dataclasses import asdict, dataclass
from datetime import datetime, timezone

import pandas as pd


REQUIRED_COLUMNS = ("日期", "品类", "销售额", "销量", "退货量", "渠道")
COLUMN_ALIASES = {
    "日期": ("日期", "date", "order_date", "交易日期"),
    "品类": ("品类", "category", "商品品类", "类目"),
    "销售额": ("销售额", "sales", "revenue", "gmv", "实付金额"),
    "销量": ("销量", "quantity", "qty", "sales_volume", "件数"),
    "退货量": ("退货量", "returns", "return_quantity", "退款件数"),
    "渠道": ("渠道", "channel", "sales_channel", "平台"),
}


@dataclass(frozen=True)
class DataSource:
    source_id: str
    name: str
    path: str
    file_sha256: str
    loaded_at: str
    row_count: int
    columns: list[str]
    column_mapping: dict[str, str]
    quality: dict

    def to_dict(self) -> dict:
        return asdict(self)


def _fingerprint(path: str) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _resolve_mapping(columns, explicit: dict[str, str] | None = None) -> dict[str, str]:
    explicit = explicit or {}
    normalized = {str(column).strip().lower(): str(column) for column in columns}
    mapping = {}
    for standard in REQUIRED_COLUMNS:
        candidate = explicit.get(standard)
        if candidate and candidate in columns:
            mapping[candidate] = standard
            continue
        for alias in COLUMN_ALIASES[standard]:
            if alias.lower() in normalized:
                mapping[normalized[alias.lower()]] = standard
                break
    missing = [name for name in REQUIRED_COLUMNS if name not in mapping.values()]
    if missing:
        raise ValueError(f"缺少必需字段：{'、'.join(missing)}；收到字段：{list(columns)}")
    return mapping


def load_enterprise_data(path: str, column_mapping: dict[str, str] | None = None) -> tuple[pd.DataFrame, DataSource]:
    """读取并标准化企业数据，返回 DataFrame 与来源元数据。"""
    if not os.path.isfile(path):
        raise FileNotFoundError(f"数据文件不存在：{path}")
    suffix = os.path.splitext(path)[1].lower()
    if suffix not in {".csv", ".xlsx", ".xls"}:
        raise ValueError("仅支持 CSV、XLSX、XLS 数据文件")
    raw = pd.read_excel(path) if suffix in {".xlsx", ".xls"} else pd.read_csv(path)
    if raw.empty:
        raise ValueError("数据文件没有记录")
    mapping = _resolve_mapping(raw.columns, column_mapping)
    frame = raw.rename(columns=mapping).loc[:, list(REQUIRED_COLUMNS)].copy()
    frame["日期"] = pd.to_datetime(frame["日期"], errors="coerce")
    for column in ("销售额", "销量", "退货量"):
        frame[column] = pd.to_numeric(frame[column], errors="coerce")

    invalid_rows = frame[list(REQUIRED_COLUMNS)].isna().any(axis=1)
    negative_rows = (frame[["销售额", "销量", "退货量"]] < 0).any(axis=1)
    impossible_returns = frame["退货量"] > frame["销量"]
    duplicate_rows = frame.duplicated()
    quality = {
        "invalid_rows": int(invalid_rows.sum()),
        "negative_rows": int(negative_rows.sum()),
        "returns_over_sales_rows": int(impossible_returns.sum()),
        "duplicate_rows": int(duplicate_rows.sum()),
        "date_min": frame["日期"].min().isoformat() if frame["日期"].notna().any() else None,
        "date_max": frame["日期"].max().isoformat() if frame["日期"].notna().any() else None,
    }
    fatal = invalid_rows | negative_rows | impossible_returns
    if fatal.any():
        raise ValueError(
            "数据质量校验失败："
            f"空值/类型错误 {quality['invalid_rows']} 行，负数 {quality['negative_rows']} 行，"
            f"退货量大于销量 {quality['returns_over_sales_rows']} 行"
        )
    sha256 = _fingerprint(path)
    source = DataSource(
        source_id=f"data:{sha256[:12]}",
        name=os.path.basename(path),
        path=os.path.abspath(path),
        file_sha256=sha256,
        loaded_at=datetime.now(timezone.utc).isoformat(),
        row_count=len(frame),
        columns=list(REQUIRED_COLUMNS),
        column_mapping=mapping,
        quality=quality,
    )
    return frame, source
