"""
数据汇聚：清洗、格式标准化。适配各业务 Cell 数据结构，统一为标准字段+payload。
不侵入 Cell，Cell 仅需 POST 标准 body；清洗与标准化在数据湖侧完成。
"""
from __future__ import annotations

import re
import time
from typing import Any, Dict, List, Optional

# 标准日期格式
ISO_FMT = "%Y-%m-%dT%H:%M:%SZ"
DATE_ONLY = "%Y-%m-%d"


def _normalize_value(v: Any) -> Any:
    """格式标准化：空字符串转 None，日期字符串尝试统一格式。"""
    if v is None:
        return None
    if isinstance(v, str):
        s = v.strip()
        if s == "":
            return None
        # 常见日期格式转时间戳（保留原始亦可，此处仅做清洗）
        if re.match(r"^\d{4}-\d{2}-\d{2}", s):
            return s[:10] if len(s) >= 10 else s
        return s
    if isinstance(v, (int, float, bool)):
        return v
    if isinstance(v, dict):
        return {k: _normalize_value(v2) for k, v2 in v.items()}
    if isinstance(v, list):
        return [_normalize_value(x) for x in v]
    return v


def cleanse_record(record: Dict[str, Any], options: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    单条清洗：去空、标准化字段。options 可含 drop_empty: bool, date_fields: []。
    """
    options = options or {}
    out = {}
    drop_empty = options.get("drop_empty", True)
    for k, v in record.items():
        if k.startswith("_"):
            out[k] = v
            continue
        vn = _normalize_value(v)
        if drop_empty and vn is None:
            continue
        out[k] = vn
    return out


def normalize_batch(
    records: List[Dict[str, Any]],
    tenant_id: str,
    cell_id: str,
    table: str,
    sync_type: str = "incremental",
    cleanse_options: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    """
    批量清洗与标准化，输出带 _meta 的标准结构供 store 写入。
    """
    out = []
    ts = time.time()
    for i, r in enumerate(records):
        if not isinstance(r, dict):
            continue
        cleaned = cleanse_record(r, cleanse_options)
        cleaned["_meta"] = {
            "tenant_id": tenant_id,
            "cell_id": cell_id,
            "table": table,
            "sync_type": sync_type,
            "ts": ts,
            "index": i,
        }
        out.append(cleaned)
    return out
