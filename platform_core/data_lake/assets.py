"""
数据资产管理：元数据、血缘追踪、数据质量校验、敏感数据识别。
所有数据按 tenant_id 隔离。
"""
from __future__ import annotations

import threading
from typing import Any, Dict, List, Optional

# 敏感类型标签
SENSITIVE_PII = "pii"
SENSITIVE_PHONE = "phone"
SENSITIVE_IDNO = "idno"
SENSITIVE_EMAIL = "email"


class MetadataCatalog:
    """元数据：tenant_id + cell_id + table -> 表/列信息、来源、更新时间。"""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._tables: Dict[tuple, Dict[str, Any]] = {}  # (tenant_id, cell_id, table) -> meta

    def register(self, tenant_id: str, cell_id: str, table: str, columns: List[Dict[str, Any]]) -> None:
        with self._lock:
            key = (tenant_id or "default", cell_id.strip().lower(), table.strip())
            self._tables[key] = {
                "tenant_id": key[0],
                "cell_id": key[1],
                "table": key[2],
                "columns": list(columns),
                "updated_at": __import__("time").time(),
            }

    def get(self, tenant_id: str, cell_id: str, table: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            key = (tenant_id or "default", cell_id.strip().lower(), table.strip())
            return dict(self._tables[key]) if key in self._tables else None

    def list_tables(self, tenant_id: str) -> List[Dict[str, Any]]:
        with self._lock:
            return [
                dict(v)
                for k, v in self._tables.items()
                if k[0] == (tenant_id or "default")
            ]


class LineageStore:
    """血缘：记录数据来源 cell、接口、同步类型、时间。"""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._lineage: Dict[str, Dict[str, Any]] = {}  # (tenant_id, cell_id, table) -> { source, endpoint, sync_type, ts }

    def record(self, tenant_id: str, cell_id: str, table: str, source: str = "push", endpoint: str = "", sync_type: str = "incremental") -> None:
        with self._lock:
            key = f"{tenant_id}|{cell_id}|{table}"
            self._lineage[key] = {
                "tenant_id": tenant_id,
                "cell_id": cell_id,
                "table": table,
                "source": source,
                "endpoint": endpoint or f"POST /api/datalake/ingest",
                "sync_type": sync_type,
                "ts": __import__("time").time(),
            }

    def get(self, tenant_id: str, cell_id: str, table: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            key = f"{tenant_id}|{cell_id}|{table}"
            return dict(self._lineage[key]) if key in self._lineage else None


class QualityRules:
    """数据质量规则：表/列级规则，校验结果。"""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._rules: Dict[tuple, List[Dict]] = {}  # (tenant_id, cell_id, table) -> [ { column, rule, params } ]
        self._results: List[Dict] = []  # 最近校验结果

    def add_rule(self, tenant_id: str, cell_id: str, table: str, column: str, rule: str, params: Optional[Dict] = None) -> None:
        with self._lock:
            key = (tenant_id or "default", cell_id.strip().lower(), table.strip())
            if key not in self._rules:
                self._rules[key] = []
            self._rules[key].append({"column": column, "rule": rule, "params": params or {}})

    def get_rules(self, tenant_id: str, cell_id: str, table: str) -> List[Dict[str, Any]]:
        with self._lock:
            key = (tenant_id or "default", cell_id.strip().lower(), table.strip())
            return list(self._rules.get(key, []))

    def record_result(self, tenant_id: str, cell_id: str, table: str, passed: bool, details: str = "") -> None:
        with self._lock:
            self._results.append({
                "tenant_id": tenant_id,
                "cell_id": cell_id,
                "table": table,
                "passed": passed,
                "details": details,
                "ts": __import__("time").time(),
            })
            if len(self._results) > 1000:
                self._results.pop(0)


class SensitiveTagger:
    """敏感数据识别：列级标签（pii/phone/idno/email），用于导出脱敏。"""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._tags: Dict[tuple, Dict[str, str]] = {}  # (tenant_id, cell_id, table) -> { column: tag }

    def tag(self, tenant_id: str, cell_id: str, table: str, column: str, tag: str) -> None:
        with self._lock:
            key = (tenant_id or "default", cell_id.strip().lower(), table.strip())
            if key not in self._tags:
                self._tags[key] = {}
            self._tags[key][column] = tag

    def get_tags(self, tenant_id: str, cell_id: str, table: str) -> Dict[str, str]:
        with self._lock:
            key = (tenant_id or "default", cell_id.strip().lower(), table.strip())
            return dict(self._tags.get(key, {}))

    def mask_value(self, value: Any, tag: str) -> Any:
        """按标签脱敏（用于导出）。"""
        if value is None:
            return None
        s = str(value).strip()
        if not s:
            return s
        if tag == SENSITIVE_PHONE and len(s) >= 7:
            return s[:3] + "****" + s[-4:]
        if tag == SENSITIVE_IDNO and len(s) >= 8:
            return s[:4] + "**********" + s[-4:]
        if tag == SENSITIVE_EMAIL and "@" in s:
            a, b = s.split("@", 1)
            return (a[:2] + "***" if len(a) > 2 else "***") + "@" + b
        if tag == SENSITIVE_PII:
            return "***"
        return s


# 单例
_catalog: Optional[MetadataCatalog] = None
_lineage: Optional[LineageStore] = None
_quality: Optional[QualityRules] = None
_sensitive: Optional[SensitiveTagger] = None
_lock = threading.Lock()


def get_catalog() -> MetadataCatalog:
    global _catalog
    if _catalog is None:
        with _lock:
            if _catalog is None:
                _catalog = MetadataCatalog()
    return _catalog


def get_lineage() -> LineageStore:
    global _lineage
    if _lineage is None:
        with _lock:
            if _lineage is None:
                _lineage = LineageStore()
    return _lineage


def get_quality() -> QualityRules:
    global _quality
    if _quality is None:
        with _lock:
            if _quality is None:
                _quality = QualityRules()
    return _quality


def get_sensitive() -> SensitiveTagger:
    global _sensitive
    if _sensitive is None:
        with _lock:
            if _sensitive is None:
                _sensitive = SensitiveTagger()
    return _sensitive
