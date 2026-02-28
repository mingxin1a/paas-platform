"""
平台级核心业务全链路 E2E：可调用 deploy/core_business_flow_tests.py。
需 GATEWAY_URL 与网关、细胞运行；CI 中可设 E2E_FULL_FLOW=1 执行全量。
"""
import os
import subprocess
import sys
import pytest

RUN_FULL = os.environ.get("E2E_FULL_FLOW", "0") == "1"


@pytest.mark.skipif(not RUN_FULL, reason="E2E_FULL_FLOW=1 and gateway+cells required")
def test_core_business_flow_script():
    root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    script = os.path.join(root, "deploy", "core_business_flow_tests.py")
    if not os.path.isfile(script):
        pytest.skip("core_business_flow_tests.py not found")
    env = os.environ.copy()
    env.setdefault("GATEWAY_URL", "http://localhost:8000")
    result = subprocess.run(
        [sys.executable, script],
        cwd=os.path.join(root, "deploy"),
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert result.returncode == 0, (result.stdout or "") + (result.stderr or "")
