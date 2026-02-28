"""
全平台操作审计日志：落盘即不可删改（仅追加），支持检索与导出。
日志写入 glass_house/operation_audit.log（追加模式）；网关在每次请求后追加一条。
每条记录含 lineHash（SHA256 前 16 字符）供事后校验完整性，实现操作日志不可篡改。
"""
from __future__ import annotations

import hashlib
import os
import json
import time
import threading
from typing import Any, Dict, List, Optional

_ROOT = os.environ.get("SUPERPAAS_ROOT", "")
_AUDIT_DIR = os.path.join(_ROOT, "glass_house") if _ROOT else ""
_AUDIT_FILE = os.path.join(_AUDIT_DIR, "operation_audit.log") if _AUDIT_DIR else ""
_LOCK = threading.Lock()
# 内存缓存最近 N 条供检索（可选）
_MEM_CACHE: List[Dict[str, Any]] = []
_MEM_CACHE_MAX = int(os.environ.get("GATEWAY_AUDIT_MEM_CACHE_MAX", "5000"))


def _ensure_dir() -> bool:
    if not _AUDIT_DIR:
        return False
    try:
        os.makedirs(_AUDIT_DIR, exist_ok=True)
        return True
    except Exception:
        return False


def _line_hash(record: Dict[str, Any]) -> str:
    """计算记录内容哈希（不含 lineHash 自身），用于不可篡改校验。"""
    payload = json.dumps(record, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def append(method: str, path: str, status: int, duration_ms: int, trace_id: str = "",
           tenant_id: str = "", user: str = "", cell: str = "", ip: str = "", extra: Optional[Dict] = None) -> None:
    """追加一条操作审计记录（仅追加，不可删改）；含 lineHash 供事后校验。"""
    ts = time.time()
    record = {
        "ts": ts,
        "time": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(ts)),
        "method": method,
        "path": path,
        "status": status,
        "durationMs": duration_ms,
        "traceId": trace_id or "",
        "tenantId": tenant_id or "",
        "user": user or "",
        "cell": cell or "",
        "ip": ip or "",
        **(extra or {}),
    }
    record["lineHash"] = _line_hash(record)
    line = json.dumps(record, ensure_ascii=False) + "\n"
    if _ensure_dir() and _AUDIT_FILE:
        try:
            with _LOCK:
                with open(_AUDIT_FILE, "a", encoding="utf-8") as f:
                    f.write(line)
                _MEM_CACHE.append(record)
                if len(_MEM_CACHE) > _MEM_CACHE_MAX:
                    _MEM_CACHE.pop(0)
        except Exception:
            pass


def search(since_ts: float = 0, to_ts: Optional[float] = None, trace_id: str = "", tenant_id: str = "",
           cell: str = "", limit: int = 100) -> List[Dict[str, Any]]:
    """检索审计日志。优先从内存缓存取；否则读文件（若存在）。"""
    out: List[Dict[str, Any]] = []
    with _LOCK:
        src = _MEM_CACHE if _MEM_CACHE else _read_file_since(since_ts, to_ts, limit * 2)
        for r in src:
            if r.get("ts", 0) < since_ts:
                continue
            if to_ts is not None and r.get("ts", 0) > to_ts:
                continue
            if trace_id and r.get("traceId") != trace_id:
                continue
            if tenant_id and r.get("tenantId") != tenant_id:
                continue
            if cell and r.get("cell") != cell:
                continue
            out.append(r)
            if len(out) >= limit:
                break
    return out


def _read_file_since(since_ts: float, to_ts: Optional[float], max_lines: int) -> List[Dict[str, Any]]:
    """从文件尾部读取最近记录。"""
    if not _AUDIT_FILE or not os.path.isfile(_AUDIT_FILE):
        return []
    result = []
    try:
        with open(_AUDIT_FILE, "r", encoding="utf-8") as f:
            lines = f.readlines()
        for line in reversed(lines[-max_lines:] if len(lines) > max_lines else lines):
            line = line.strip()
            if not line:
                continue
            try:
                r = json.loads(line)
                if r.get("ts", 0) >= since_ts and (to_ts is None or r.get("ts", 0) <= to_ts):
                    result.append(r)
            except Exception:
                continue
    except Exception:
        pass
    return result


def export_path() -> Optional[str]:
    """返回审计日志文件路径（供导出下载）。"""
    if _AUDIT_FILE and os.path.isfile(_AUDIT_FILE):
        return _AUDIT_FILE
    return None
