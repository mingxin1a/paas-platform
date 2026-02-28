"""
00 修正案 #5 抗抵赖 / 01 5.2 不可抵赖性 - 细胞侧验签
与网关 signing 算法一致：HMAC-SHA256(method|path|body|X-Request-ID|X-Tenant-Id|X-Trace-Id|timestamp)
密钥：CELL_SIGNING_SECRET（与 GATEWAY_SIGNING_SECRET 一致）；未配置则跳过验签。
"""
from __future__ import annotations

import os
import hmac
import hashlib
import time
import base64
import json
import logging

SIGNATURE_HEADER = "X-Signature"
SIGNATURE_TIME_HEADER = "X-Signature-Time"
SIGNED_HEADERS = ("X-Request-ID", "X-Tenant-Id", "X-Trace-Id")
TIME_WINDOW_SEC = 300


def _get_secret() -> bytes | None:
    raw = os.environ.get("CELL_SIGNING_SECRET")
    if not raw:
        return None
    raw = raw.strip()
    if raw.startswith("base64:"):
        try:
            return base64.b64decode(raw[7:].strip())
        except Exception:
            return raw.encode("utf-8")
    return raw.encode("utf-8")


def _compute_expected(method: str, path: str, body: bytes, headers: dict, timestamp: int) -> str:
    secret = _get_secret()
    if not secret:
        return ""
    parts = [method.upper(), path or "/", body or b""]
    for h in SIGNED_HEADERS:
        parts.append((headers.get(h) or "").encode("utf-8"))
    parts.append(str(timestamp).encode("utf-8"))
    payload = b"|".join(parts)
    return hmac.new(secret, payload, hashlib.sha256).hexdigest()


def verify_signature(method: str, path: str, body: bytes, headers: dict) -> tuple[bool, str]:
    """返回 (通过, 失败原因)。"""
    if not _get_secret():
        return True, ""
    sig = (headers.get(SIGNATURE_HEADER) or "").strip()
    ts_str = (headers.get(SIGNATURE_TIME_HEADER) or "").strip()
    if not sig or not ts_str:
        return False, "missing_signature_or_timestamp"
    try:
        ts = int(ts_str)
    except ValueError:
        return False, "invalid_timestamp"
    if abs(int(time.time()) - ts) > TIME_WINDOW_SEC:
        return False, "timestamp_out_of_window"
    expected = _compute_expected(method, path, body, headers, ts)
    if not expected or not hmac.compare_digest(expected, sig):
        return False, "signature_mismatch"
    return True, ""


def write_security_audit(event: str, detail: str, path: str = "", trace_id: str = "") -> None:
    """验签失败时写入安全审计（黑客入侵日志），01 5.2 / 00 #5。"""
    line = json.dumps({
        "event": event,
        "detail": detail,
        "path": path,
        "trace_id": trace_id,
        "ts": time.time(),
    }, ensure_ascii=False) + "\n"
    logging.getLogger("security_audit").warning(line.strip())
    p = os.environ.get("CELL_SECURITY_AUDIT_PATH")
    if p:
        try:
            with open(p, "a", encoding="utf-8") as f:
                f.write(line)
        except Exception:
            pass
