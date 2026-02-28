#!/usr/bin/env python3
"""
一键执行全项目测试：PaaS 核心层单元测试、各 Cell 单元测试、集成测试、边界测试；
可选 E2E（Playwright）。生成覆盖率与结果报告。
用法:
  python scripts/run_all_tests.py
  python scripts/run_all_tests.py --no-cells
  python scripts/run_all_tests.py --e2e
  python scripts/run_all_tests.py --report-dir ./test-reports
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys


ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
CELLS_BATCH1 = ["crm", "erp", "oa", "srm"]
CELLS_BATCH2 = ["mes", "wms", "tms"]
CELLS_BATCH3 = ["ems", "plm", "his", "lis", "lims", "hrm"]


def run(cmd: list[str], cwd: str = ROOT, env: dict | None = None) -> int:
    env = env or os.environ.copy()
    env.setdefault("PYTHONPATH", ROOT)
    if "PATH" in os.environ:
        env["PATH"] = os.environ["PATH"]
    p = subprocess.run(cmd, cwd=cwd, env=env)
    return p.returncode


def main() -> int:
    ap = argparse.ArgumentParser(description="一键运行全项目测试")
    ap.add_argument("--no-cells", action="store_true", help="跳过各 Cell 单元测试")
    ap.add_argument("--no-integration", action="store_true", help="跳过集成测试")
    ap.add_argument("--no-boundary", action="store_true", help="跳过边界测试")
    ap.add_argument("--e2e", action="store_true", help="运行 Playwright E2E（需安装 playwright 且可选启动服务）")
    ap.add_argument("--report-dir", default=os.path.join(ROOT, "test-reports"), help="测试报告与覆盖率输出目录")
    ap.add_argument("--coverage", action="store_true", default=True, help="生成覆盖率（默认开启）")
    args = ap.parse_args()

    os.makedirs(args.report_dir, exist_ok=True)
    failed = 0

    # 1. PaaS 核心层单元测试
    print("\n=== PaaS 核心层单元测试 ===")
    cov_platform = ["--cov=platform_core", "--cov-report=term-missing", f"--cov-report=html:{args.report_dir}/coverage_platform", f"--cov-report=xml:{args.report_dir}/coverage_platform.xml"] if args.coverage else []
    code = run([sys.executable, "-m", "pytest", "tests/unit_platform/", "-v", "--tb=short"] + cov_platform)
    if code != 0:
        failed += 1

    # 2. 各 Cell 单元测试
    if not args.no_cells:
        for batch, cells in [("批次1", CELLS_BATCH1), ("批次2", CELLS_BATCH2), ("批次3", CELLS_BATCH3)]:
            print(f"\n=== Cell 单元测试 {batch} ===")
            for cell in cells:
                cell_path = os.path.join(ROOT, "cells", cell)
                if not os.path.isdir(cell_path):
                    continue
                cov_cell = ["--cov=src", "--cov-report=term-missing", f"--cov-report=xml:{cell_path}/coverage.xml"] if args.coverage else []
                code = run([sys.executable, "-m", "pytest", "tests/", "-v", "--tb=short"] + cov_cell, cwd=cell_path)
                if code != 0:
                    failed += 1

    # 3. 平台层通用测试（健康、契约、验收等，不含 unit_platform/integration）
    print("\n=== 平台通用测试（健康/契约/验收） ===")
    code = run([sys.executable, "-m", "pytest", "tests/", "-v", "--tb=short", "-k", "not test_core_business_flow_script and not USE_REAL", "--ignore=tests/unit_platform/", "--ignore=tests/integration/", "--ignore=tests/e2e/", "--ignore=tests/e2e_playwright/", "--ignore=tests/boundary/"])
    if code != 0:
        failed += 1

    # 4. 集成测试
    if not args.no_integration:
        print("\n=== 集成测试 ===")
        code = run([sys.executable, "-m", "pytest", "tests/integration/", "-v", "--tb=short"])
        if code != 0:
            failed += 1

    # 5. 边界测试
    if not args.no_boundary:
        print("\n=== 边界测试 ===")
        code = run([sys.executable, "-m", "pytest", "tests/boundary/", "-v", "--tb=short"])
        if code != 0:
            failed += 1

    # 6. E2E（可选）
    if args.e2e:
        print("\n=== E2E Playwright ===")
        code = run([sys.executable, "-m", "pytest", "tests/e2e_playwright/", "-v", "--tb=short"])
        if code != 0:
            failed += 1

    print(f"\n>>> 测试完成，失败套件数: {failed}")
    if args.coverage and not failed:
        print(f">>> 覆盖率报告: {args.report_dir}/coverage_platform/ (PaaS 层)")
    return min(failed, 255)


if __name__ == "__main__":
    sys.exit(main())
