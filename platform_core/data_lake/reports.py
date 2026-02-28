"""
统一报表引擎：报表定义、查询、可视化大屏数据接口、数据导出。
适配所有业务 Cell 的数据分析需求；数据来自数据湖已汇聚数据，按权限过滤。
"""
from __future__ import annotations

import csv
import io
import threading
from typing import Any, Dict, List, Optional

from .store import get_store
from .permission import get_permission_store


class ReportStore:
    """报表定义：id, name, tenant_id, datasource(cell+table 或 view), dimensions, metrics, filters。"""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._reports: Dict[str, Dict[str, Any]] = {}
        self._dashboards: Dict[str, Dict[str, Any]] = {}  # 大屏：id -> { name, widgets[], layout }

    def save_report(self, report_id: str, tenant_id: str, name: str, datasource: Dict[str, Any],
                    dimensions: List[str], metrics: List[str], filters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        with self._lock:
            r = {
                "id": report_id,
                "tenant_id": tenant_id or "default",
                "name": name,
                "datasource": datasource or {},
                "dimensions": list(dimensions or []),
                "metrics": list(metrics or []),
                "filters": dict(filters or {}),
            }
            self._reports[report_id] = r
            return dict(r)

    def get_report(self, report_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            return dict(self._reports[report_id]) if report_id in self._reports else None

    def list_reports(self, tenant_id: str) -> List[Dict[str, Any]]:
        with self._lock:
            return [dict(r) for r in self._reports.values() if r.get("tenant_id") == (tenant_id or "default")]

    def save_dashboard(self, dashboard_id: str, tenant_id: str, name: str, widgets: List[Dict], layout: Optional[Dict] = None) -> Dict[str, Any]:
        with self._lock:
            d = {
                "id": dashboard_id,
                "tenant_id": tenant_id or "default",
                "name": name,
                "widgets": list(widgets or []),
                "layout": layout or {},
            }
            self._dashboards[dashboard_id] = d
            return dict(d)

    def get_dashboard(self, dashboard_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            return dict(self._dashboards[dashboard_id]) if dashboard_id in self._dashboards else None

    def list_dashboards(self, tenant_id: str) -> List[Dict[str, Any]]:
        with self._lock:
            return [dict(d) for d in self._dashboards.values() if d.get("tenant_id") == (tenant_id or "default")]


_report_store: Optional[ReportStore] = None
_report_lock = threading.Lock()


def get_report_store() -> ReportStore:
    global _report_store
    if _report_store is None:
        with _report_lock:
            if _report_store is None:
                _report_store = ReportStore()
    return _report_store


def run_report(report_id: str, tenant_id: str, role: str, limit: int = 1000) -> List[Dict[str, Any]]:
    """执行报表：从数据湖取数，按权限过滤，返回维度+指标。"""
    store = get_store()
    perm = get_permission_store()
    repo = get_report_store()
    r = repo.get_report(report_id)
    if not r or r.get("tenant_id") != (tenant_id or "default"):
        return []
    ds = r.get("datasource") or {}
    cell_id = ds.get("cell_id")
    table = ds.get("table")
    if not cell_id or not table:
        return []
    rows = store.query(tenant_id=tenant_id, cell_id=cell_id, table=table, limit=limit)
    rows = perm.apply_row_filter(tenant_id, role, cell_id, table, rows)
    # 简化：取 payload，按 dimensions/metrics 投影
    dims = r.get("dimensions") or []
    metrics = r.get("metrics") or []
    cols = list(set(dims) | set(metrics))
    all_cols = (list(rows[0].get("payload", {}).keys()) if rows else []) if not cols else cols
    cols = perm.filter_allowed_columns(tenant_id, role, cell_id, table, all_cols)
    out = []
    for rec in rows:
        payload = rec.get("payload") or rec
        out.append({k: payload.get(k) for k in cols if k in payload})
    return out


def export_csv(data: List[Dict[str, Any]]) -> str:
    """导出为 CSV 字符串。"""
    if not data:
        return ""
    buf = io.StringIO()
    keys = list(data[0].keys()) if data else []
    w = csv.DictWriter(buf, fieldnames=keys, extrasaction="ignore")
    w.writeheader()
    w.writerows(data)
    return buf.getvalue()
