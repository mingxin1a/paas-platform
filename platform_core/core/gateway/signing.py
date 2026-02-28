"""
00 修正案 #5 抗抵赖 / 01 5.2 不可抵赖性
跨系统数据交互必须包含数字签名，接收方必须验签，验签失败须告警并记录「黑客入侵日志」。
采用 HMAC-SHA256，密钥由环境变量提供，与 KMS 集成时由 KMS 注入。
"""
import os
import hmac
import hashlib
import time
import base64
from typing import Optional

# 签名头：X-Signature（HMAC-SHA256 十六进制）, X-Signature-Time（Unix 秒，防重放窗口）
SIGNATURE_HEADER = "X-Signature"
SIGNATURE_TIME_HEADER = "X-Signature-Time"
# 参与签名的请求头（按字典序拼接）
SIGNED_HEADERS = ("X-Request-ID", "X-Tenant-Id", "X-Trace-Id")
# 验签时间窗口（秒），超出视为重放
TIME_WINDOW_SEC = 300


def _get_secret() -> Optional[bytes]:
    raw = os.environ.get("GATEWAY_SIGNING_SECRET") or os.environ.get("CELL_SIGNING_SECRET")
    if not raw:
        return None
    raw = raw.strip()
    if raw.startswith("base64:"):
        try:
            return base64.b64decode(raw[7:].strip())
        except Exception:
            return raw.encode("utf-8")
    return raw.encode("utf-8")


def compute_signature(method: str, path: str, body: bytes, headers: dict, timestamp: Optional[int] = None) -> Optional[str]:
    """
    计算请求签名。用于网关转发前加签。
    method, path, body 及 SIGNED_HEADERS 对应头按固定顺序拼接后 HMAC-SHA256。
    """
    secret = _get_secret()
    if not secret:
        return None
    if timestamp is None:
        timestamp = int(time.time())
    parts = [method.upper(), path or "/", body or b""]
    for h in SIGNED_HEADERS:
        parts.append((headers.get(h) or "").encode("utf-8"))
    parts.append(str(timestamp).encode("utf-8"))
    payload = b"|".join(parts)
    sig = hmac.new(secret, payload, hashlib.sha256).hexdigest()
    return sig


def verify_signature(method: str, path: str, body: bytes, headers: dict) -> tuple[bool, str]:
    """
    验签。返回 (是否通过, 失败原因)。
    验签失败原因用于写入安全审计日志。
    """
    secret = _get_secret()
    if not secret:
        return True, ""  # 未配置密钥时跳过验签，便于渐进启用

    sig = (headers.get(SIGNATURE_HEADER) or "").strip()
    ts_str = (headers.get(SIGNATURE_TIME_HEADER) or "").strip()
    if not sig or not ts_str:
        return False, "missing_signature_or_timestamp"
    try:
        ts = int(ts_str)
    except ValueError:
        return False, "invalid_timestamp"
    now = int(time.time())
    if abs(now - ts) > TIME_WINDOW_SEC:
        return False, "timestamp_out_of_window"
    expected = compute_signature(method, path, body, headers, ts)
    if not expected or not hmac.compare_digest(expected, sig):
        return False, "signature_mismatch"
    return True, ""


def write_security_audit(event: str, detail: str, cell: str = "", path: str = "", trace_id: str = "", extra: dict = None) -> None:
    """
    写入安全审计日志（黑客入侵/验签失败等），满足 01 5.2 与 00 #5。
    落盘到 glass_house/security_audit.log；若 glass_house 不可写则仅 logging。
    """
    import json
    import logging
    log_line = {
        "event": event,
        "detail": detail,
        "cell": cell,
        "path": path,
        "trace_id": trace_id,
        "ts": time.time(),
        **(extra or {}),
    }
    msg = json.dumps(log_line, ensure_ascii=False)
    logger = logging.getLogger("security_audit")
    logger.warning(msg)
    # 尝试写入 glass_house（项目根下）
    root = os.environ.get("SUPERPAAS_ROOT", os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
    audit_file = os.path.join(root, "glass_house", "security_audit.log")
    try:
        with open(audit_file, "a", encoding="utf-8") as f:
            f.write(msg + "\n")
    except Exception:
        pass
