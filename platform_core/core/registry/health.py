"""
细胞健康检查与自动扩缩容
《01_核心法律》细胞自治：独立失效、独立扩缩容。
量化驱动：健康状态可观测；扩缩容建议可对接监控指标。
"""
import threading
import time
from typing import Callable, Dict, Optional

try:
    import urllib.request
    _urlopen = urllib.request.urlopen
except Exception:
    _urlopen = None


class HealthChecker:
    """对已注册细胞周期性 GET /health，失败 N 次标记不健康。"""

    def __init__(self, check_interval_sec: float = 30, failure_threshold: int = 3, timeout_sec: float = 5):
        self.check_interval_sec = check_interval_sec
        self.failure_threshold = failure_threshold
        self.timeout_sec = timeout_sec
        self._healthy: Dict[str, bool] = {}
        self._failures: Dict[str, int] = {}
        self._lock = threading.Lock()
        self._stop = False
        self._thread: Optional[threading.Thread] = None

    def _do_check(self, base_url: str) -> bool:
        if not _urlopen:
            return True
        try:
            req = urllib.request.Request(f"{base_url.rstrip('/')}/health", method="GET")
            resp = _urlopen(req, timeout=self.timeout_sec)
            return 200 <= resp.status < 300
        except Exception:
            return False

    def check_one(self, cell_name: str, base_url: str) -> bool:
        ok = self._do_check(base_url)
        with self._lock:
            if not ok:
                self._failures[cell_name] = self._failures.get(cell_name, 0) + 1
                self._healthy[cell_name] = self._failures[cell_name] < self.failure_threshold
            else:
                self._failures[cell_name] = 0
                self._healthy[cell_name] = True
            return self._healthy[cell_name]

    def is_healthy(self, cell_name: str) -> bool:
        with self._lock:
            return self._healthy.get(cell_name, True)

    def start_background(self, get_cells_and_urls: Callable[[], list]) -> None:
        """后台线程周期性检查；get_cells_and_urls() 返回 [(cell_name, base_url), ...]。"""

        def _loop():
            while not self._stop:
                try:
                    for cell_name, base_url in get_cells_and_urls():
                        if self._stop:
                            break
                        self.check_one(cell_name, base_url)
                except Exception:
                    pass
                time.sleep(self.check_interval_sec)

        self._thread = threading.Thread(target=_loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop = True
        if self._thread:
            self._thread.join(timeout=2)


class AutoscalePolicy:
    """扩缩容建议：根据错误率/延迟建议 scale_up 或 scale_down（仅输出建议，不执行）。"""

    def __init__(self, error_rate_scale_up: float = 0.05, latency_p99_scale_up_ms: float = 500):
        self.error_rate_scale_up = error_rate_scale_up
        self.latency_p99_scale_up_ms = latency_p99_scale_up_ms

    def suggest(self, cell_name: str, error_rate: float, latency_p99_ms: float) -> str:
        """返回 up | down | none。"""
        if error_rate >= self.error_rate_scale_up or latency_p99_ms >= self.latency_p99_scale_up_ms:
            return "up"
        if error_rate < 0.01 and latency_p99_ms < 100:
            return "down"
        return "none"
