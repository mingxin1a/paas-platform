"""
治理中心存储：注册表、健康状态、链路 span、RED 指标
线程安全，内存存储；不侵入业务细胞。
性能优化：Span 分片降低锁竞争；指标按 cell 分表；冷热分离（近期 trace 热表，超量淘汰）。
"""
import os
import threading
import time
from collections import deque
from typing import Any, Dict, List, Optional

# 链路保留条数及 TTL（秒）
SPAN_MAX_PER_TRACE = 50
SPAN_TTL_SEC = 3600
# 指标滑动窗口（条数）；可缩小以降低 get_metrics 排序成本
METRICS_WINDOW = int(os.environ.get("GOVERNANCE_METRICS_WINDOW", "1000"))
# Span 分片数（按 trace_id hash 分片，降低锁竞争）
SPAN_SHARDS = int(os.environ.get("GOVERNANCE_SPAN_SHARDS", "16"))
# 热数据：单分片内最大 trace 数，超量淘汰最旧（冷热分离）
SPAN_HOT_MAX_PER_SHARD = int(os.environ.get("GOVERNANCE_SPAN_HOT_MAX", "400"))


class GovernanceStore:
    """注册表 + 健康 + Span（分片）+ 指标 统一存储。"""

    def __init__(self):
        self._lock = threading.RLock()
        self._registry: Dict[str, Dict[str, Any]] = {}
        self._span_shards: List[Dict[str, List[Dict]]] = [{} for _ in range(SPAN_SHARDS)]
        self._span_shard_locks: List[threading.RLock] = [threading.RLock() for _ in range(SPAN_SHARDS)]
        self._metrics: Dict[str, Dict[str, Any]] = {}

    # ---------- 注册与发现 ----------
    def register(self, cell: str, base_url: str) -> None:
        with self._lock:
            self._registry[cell] = {
                "base_url": base_url.rstrip("/"),
                "healthy": True,
                "last_check_ts": None,
            }

    def deregister(self, cell: str) -> None:
        with self._lock:
            self._registry.pop(cell, None)
            self._metrics.pop(cell, None)

    def list_cells(self) -> List[Dict]:
        with self._lock:
            return [
                {"cell": c, "base_url": v["base_url"], "healthy": v["healthy"], "last_check_at": v.get("last_check_ts")}
                for c, v in self._registry.items()
            ]

    def get_cells_for_health_check(self) -> List[tuple]:
        """返回 [(cell, base_url), ...] 供健康巡检使用。"""
        with self._lock:
            return [(c, v["base_url"]) for c, v in self._registry.items()]

    def resolve(self, cell: str) -> Optional[str]:
        """仅返回健康细胞的 base_url，否则 None（故障隔离）。"""
        with self._lock:
            r = self._registry.get(cell)
            if not r or not r.get("healthy", True):
                return None
            return r["base_url"]

    def set_health(self, cell: str, healthy: bool, ts: Optional[float] = None) -> None:
        with self._lock:
            if cell in self._registry:
                self._registry[cell]["healthy"] = healthy
                self._registry[cell]["last_check_ts"] = ts or time.time()

    def get_health(self, cell: str) -> Optional[bool]:
        with self._lock:
            r = self._registry.get(cell)
            return r.get("healthy", True) if r else None

    def _span_shard_idx(self, trace_id: str) -> int:
        return hash(trace_id) % SPAN_SHARDS

    # ---------- 链路 Span（分片 + 冷热淘汰，分片独立锁降低竞争） ----------
    def add_span(self, trace_id: str, span_id: str, cell: str, path: str, status_code: int, duration_ms: int) -> None:
        ts = time.time()
        span = {
            "span_id": span_id,
            "cell": cell,
            "path": path,
            "status_code": status_code,
            "duration_ms": duration_ms,
            "ts": ts,
        }
        idx = self._span_shard_idx(trace_id)
        shard = self._span_shards[idx]
        lock = self._span_shard_locks[idx]
        with lock:
            if trace_id not in shard:
                shard[trace_id] = []
            arr = shard[trace_id]
            arr.append(span)
            if len(arr) > SPAN_MAX_PER_TRACE:
                arr.pop(0)
            if len(shard) > SPAN_HOT_MAX_PER_SHARD:
                by_ts = sorted(shard.keys(), key=lambda k: (shard[k][-1]["ts"] if shard[k] else 0))
                for k in by_ts[: len(shard) - SPAN_HOT_MAX_PER_SHARD]:
                    shard.pop(k, None)

    def get_trace(self, trace_id: str) -> Optional[Dict]:
        idx = self._span_shard_idx(trace_id)
        shard = self._span_shards[idx]
        with self._span_shard_locks[idx]:
            spans = shard.get(trace_id, [])
            now = time.time()
            spans = [s for s in spans if now - s["ts"] < SPAN_TTL_SEC]
            if not spans:
                return None
            return {"trace_id": trace_id, "spans": spans}

    # ---------- RED 指标（请求量、成功率、响应时间） ----------
    def ingest(self, cell: str, path: str, status_code: int, duration_ms: int) -> None:
        with self._lock:
            if cell not in self._metrics:
                self._metrics[cell] = {"request_total": 0, "success_total": 0, "durations": deque(maxlen=METRICS_WINDOW)}
            m = self._metrics[cell]
            m["request_total"] = m.get("request_total", 0) + 1
            if status_code < 400:
                m["success_total"] = m.get("success_total", 0) + 1
            m["durations"].append(duration_ms)

    def get_metrics(self, cell: Optional[str] = None) -> Dict:
        """返回 RED：request_total, success_total, success_rate, duration_ms_avg, duration_ms_p50, duration_ms_p99。按 cell 分表，仅读目标 cell 时锁范围小。"""
        with self._lock:
            if cell:
                cells = [cell] if cell in self._metrics else []
            else:
                cells = list(self._metrics.keys())
            out = {}
            for c in cells:
                m = self._metrics.get(c, {})
                total = m.get("request_total", 0)
                success = m.get("success_total", 0)
                durations = list(m.get("durations", []))
                out[c] = {
                    "request_total": total,
                    "success_total": success,
                    "success_rate": (success / total if total else 0),
                    "duration_ms_avg": (sum(durations) / len(durations) if durations else 0),
                    "duration_ms_p50": _percentile(durations, 0.5),
                    "duration_ms_p99": _percentile(durations, 0.99),
                }
            return out if cell else {"cells": out}


def _percentile(sorted_durations: List[int], p: float) -> float:
    if not sorted_durations:
        return 0.0
    s = sorted(sorted_durations)
    k = (len(s) - 1) * p
    f = int(k)
    c = f + 1 if f + 1 < len(s) else f
    return float(s[f]) if f == c else s[f] + (k - f) * (s[c] - s[f])
