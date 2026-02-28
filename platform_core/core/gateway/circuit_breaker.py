"""
熔断器：《接口设计说明书》3.3.1
触发条件：可配置时间窗内异常率 >= 阈值 -> 开启。
恢复：半开状态放行少量探测请求，连续成功则关闭。
高可用：参数可通过环境变量 GATEWAY_CB_* 覆盖，便于生产调优。
"""
import os
import time
import threading
from typing import Dict, Optional

_WINDOW_SEC = 10
_FAILURE_RATIO_THRESHOLD = 0.5
_HALF_OPEN_PROBES = 3
_PROBE_SUCCESSES_TO_CLOSE = 2


def _float_env(key: str, default: float) -> float:
    try:
        return float(os.environ.get(key, default))
    except (TypeError, ValueError):
        return default


def _int_env(key: str, default: int) -> int:
    try:
        return int(os.environ.get(key, default))
    except (TypeError, ValueError):
        return default


class CircuitBreaker:
    """单细胞熔断器，线程安全。"""

    def __init__(
        self,
        cell_name: str,
        window_sec: Optional[float] = None,
        failure_ratio: Optional[float] = None,
        half_open_probes: Optional[int] = None,
        probe_successes_to_close: Optional[int] = None,
    ):
        self.cell_name = cell_name
        self.window_sec = window_sec if window_sec is not None else _float_env("GATEWAY_CB_WINDOW_SEC", _WINDOW_SEC)
        self.failure_ratio = failure_ratio if failure_ratio is not None else _float_env("GATEWAY_CB_FAILURE_RATIO", _FAILURE_RATIO_THRESHOLD)
        self._half_open_probes_limit = half_open_probes if half_open_probes is not None else _int_env("GATEWAY_CB_HALF_OPEN_PROBES", _HALF_OPEN_PROBES)
        self._probe_successes_to_close = probe_successes_to_close if probe_successes_to_close is not None else _int_env("GATEWAY_CB_PROBE_SUCCESSES_TO_CLOSE", _PROBE_SUCCESSES_TO_CLOSE)
        self._lock = threading.Lock()
        self._state = "closed"  # closed | open | half_open
        self._window_start = time.monotonic()
        self._successes = 0
        self._failures = 0
        self._half_open_successes = 0
        self._half_open_probes = 0

    def record(self, success: bool) -> None:
        with self._lock:
            now = time.monotonic()
            if now - self._window_start >= self.window_sec:
                self._window_start = now
                self._successes = 0
                self._failures = 0
            if self._state == "half_open":
                self._half_open_probes += 1
                if success:
                    self._half_open_successes += 1
                    if self._half_open_successes >= self._probe_successes_to_close:
                        self._state = "closed"
                        self._half_open_successes = 0
                        self._half_open_probes = 0
                elif self._half_open_probes >= self._half_open_probes_limit:
                    self._state = "open"
                    self._window_start = now
                    self._half_open_successes = 0
                return
            if self._state == "open":
                return
            if success:
                self._successes += 1
            else:
                self._failures += 1
            total = self._successes + self._failures
            if total >= 2 and self._failures / total >= self.failure_ratio:
                self._state = "open"
                self._window_start = now

    def allow_request(self) -> bool:
        """是否允许请求（未熔断或半开可放行）。"""
        with self._lock:
            if self._state == "closed":
                return True
            if self._state == "half_open":
                return self._half_open_probes < self._half_open_probes_limit
            if self._state == "open":
                if time.monotonic() - self._window_start >= self.window_sec:
                    self._state = "half_open"
                    self._half_open_successes = 0
                    self._half_open_probes = 0
                    return True
                return False
            return True

    def state(self) -> str:
        with self._lock:
            return self._state


class CircuitBreakerRegistry:
    """所有细胞的熔断器注册表；参数可从环境变量 GATEWAY_CB_* 读取。"""
    def __init__(self):
        self._breakers: Dict[str, CircuitBreaker] = {}
        self._lock = threading.Lock()

    def get(self, cell_name: str) -> CircuitBreaker:
        with self._lock:
            if cell_name not in self._breakers:
                self._breakers[cell_name] = CircuitBreaker(cell_name)
            return self._breakers[cell_name]


__all__ = ["CircuitBreaker", "CircuitBreakerRegistry"]
