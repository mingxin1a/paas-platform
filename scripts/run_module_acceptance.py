#!/usr/bin/env python3
"""
分模块商用验收测试脚本：仅验收指定业务模块，适配分阶段交付。
用法: python scripts/run_module_acceptance.py <cell_id>
示例: python scripts/run_module_acceptance.py crm
       python scripts/run_module_acceptance.py mes
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "scripts" / "run_acceptance_test.py"

def main():
    if len(sys.argv) < 2:
        print("用法: python scripts/run_module_acceptance.py <cell_id>")
        print("示例: python scripts/run_module_acceptance.py crm")
        sys.exit(1)
    module = sys.argv[1].strip().lower()
    allowed = ["crm", "erp", "oa", "srm", "mes", "wms", "tms", "hrm", "plm", "ems", "his", "lis", "lims"]
    if module not in allowed:
        print(f"无效模块: {module}，可选: {', '.join(allowed)}")
        sys.exit(1)
    rc = subprocess.call(
        [sys.executable, str(SCRIPT), "--module", module],
        cwd=str(ROOT),
    )
    sys.exit(rc)
