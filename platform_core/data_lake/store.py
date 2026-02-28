"""
数据湖存储：按 tenant_id + cell_id + table 隔离存储，支持全量/增量。
数据结构标准化为 { id, tenant_id, cell_id, table, sync_type, payload, ts, _meta }。
严格数据隔离：不同租户数据 100% 不互通。
"""
from __future__ import annotations

import os
import time
import threading
from collections import deque
from typing import Any, Dict, List, Optional

# 单表最大条数（可配置），超量淘汰最旧
MAX_RECORDS_PER_TABLE = int(os.environ.get("DATALAKE_MAX_RECORDS_PER_TABLE", "100000"))
# 默认每表保留条数
DEFAULT_MAX_RECORDS = min(50000, MAX_RECORDS_PER_TABLE)


class DataLakeStore:
    """按租户+细胞+表存储；支持全量/增量标识与时间序。"""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        # (tenant_id, cell_id, table) -> deque of { id, tenant_id, cell_id, table, sync_type, payload, ts, _meta }
        self._tables: Dict[tuple, deque] = {}
        self._max_per_table = DEFAULT_MAX_RECORDS

    def _key(self, tenant_id: str, cell_id: str, table: str) -> tuple:
        return (tenant_id or "default", (cell_id or "").strip().lower(), (table or "").strip())

    def ingest(
        self,
        tenant_id: str,
        cell_id: str,
        table: str,
        records: List[Dict[str, Any]],
        sync_type: str = "incremental",
    ) -> int:
        """
        写入一批记录。sync_type: full|incremental。
        full 时先清空该 tenant+cell+table 再写入；incremental 追加。
        返回写入条数。
        """
        tenant_id = tenant_id or "default"
        cell_id = (cell_id or "").strip().lower()
        table = (table or "").strip()
        if not cell_id or not table:
            return 0
        key = self._key(tenant_id, cell_id, table)
        with self._lock:
            if key not in self._tables:
                self._tables[key] = deque(maxlen=self._max_per_table)
            q = self._tables[key]
            if sync_type == "full":
                q.clear()
            ts = time.time()
            count = 0
            for i, r in enumerate(records):
                if not isinstance(r, dict):
                    continue
                rec = {
                    "id": r.get("id") or f"{tenant_id}_{cell_id}_{table}_{ts}_{i}",
                    "tenant_id": tenant_id,
                    "cell_id": cell_id,
                    "table": table,
                    "sync_type": sync_type,
                    "payload": dict(r),
                    "ts": ts,
                    "_meta": r.get("_meta") or {},
                }
                q.append(rec)
                count += 1
            return count

    def query(
        self,
        tenant_id: str,
        cell_id: Optional[str] = None,
        table: Optional[str] = None,
        since_ts: Optional[float] = None,
        limit: int = 1000,
    ) -> List[Dict[str, Any]]:
        """查询：必须带 tenant_id，按 cell/table 过滤，按 ts 过滤。仅返回当前租户数据。"""
        tenant_id = tenant_id or "default"
        with self._lock:
            out = []
            for (tid, cid, tbl), q in self._tables.items():
                if tid != tenant_id:
                    continue
                if cell_id is not None and cid != cell_id:
                    continue
                if table is not None and tbl != table:
                    continue
                for rec in q:
                    if since_ts is not None and rec.get("ts", 0) < since_ts:
                        continue
                    out.append(dict(rec))
                    if len(out) >= limit:
                        return out
            return out[:limit]

    def list_tables(self, tenant_id: str) -> List[Dict[str, Any]]:
        """列出某租户下所有 cell+table 组合（元数据用）。"""
        tenant_id = tenant_id or "default"
        seen = set()
        with self._lock:
            for (tid, cid, tbl), q in self._tables.items():
                if tid != tenant_id:
                    continue
                k = (cid, tbl)
                if k not in seen:
                    seen.add(k)
            return [{"cell_id": c, "table": t} for c, t in sorted(seen)]


_store: Optional[DataLakeStore] = None
_store_lock = threading.Lock()


def get_store() -> DataLakeStore:
    global _store
    if _store is not None:
        return _store
    with _store_lock:
        if _store is not None:
            return _store
        _store = DataLakeStore()
        return _store
