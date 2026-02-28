"""
00 元规则 #8 红绿灯原则
CPU 使用率超过阈值时自动开启「红灯模式」：只读/降级，保护数据库不被压垮。
"""
import os
import logging

_CPU_THRESHOLD = float(os.environ.get("GATEWAY_CPU_THRESHOLD", "80"))  # 默认 80%
_psutil = None

def _get_cpu_percent() -> float:
    try:
        global _psutil
        if _psutil is None:
            import psutil
            _psutil = psutil
        return _psutil.cpu_percent(interval=0)
    except Exception:
        return 0.0


def is_red_light() -> bool:
    """CPU 超过阈值时返回 True，应拒绝非只读请求。"""
    if os.environ.get("GATEWAY_TRAFFIC_LIGHT_ENABLED", "1") != "1":
        return False
    try:
        pct = _get_cpu_percent()
        return pct >= _CPU_THRESHOLD
    except Exception:
        return False


def emit_red_light_log(trace_id: str, method: str, path: str) -> None:
    """记录红灯模式拒绝请求，用于告警与审计。"""
    log = {"level": "warn", "message": "red_light_reject", "trace_id": trace_id, "method": method, "path": path}
    logging.getLogger("gateway").warning(str(log))
