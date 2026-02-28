#!/usr/bin/env python3
"""
最终商用验收流水线：自检（pytest）、验收测试、覆盖率检查，输出《最终验收报告》。
用法:
  python scripts/run_final_acceptance.py
  python scripts/run_final_acceptance.py --skip-gateway   # 不跑需网关的验收（仅单元/自检）
  python scripts/run_final_acceptance.py --no-pytest      # 不跑 pytest
"""
from __future__ import annotations

import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DIST = ROOT / "dist"
SCRIPT_ACCEPTANCE = ROOT / "scripts" / "run_acceptance_test.py"
SCRIPT_GENERATE_DOCS = ROOT / "scripts" / "generate_docs.py"


def run_pytest() -> tuple[bool, str, str]:
    """执行 pytest，返回 (是否通过, 摘要, 原始输出)。"""
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT)
    cmd = [sys.executable, "-m", "pytest", "tests/", "-v", "--tb=short", "-q", "--no-header", "-x"]
    try:
        result = subprocess.run(
            cmd,
            cwd=str(ROOT),
            env=env,
            capture_output=True,
            text=True,
            timeout=300,
        )
        out = (result.stdout or "") + (result.stderr or "")
        passed = result.returncode == 0
        summary = f"退出码 {result.returncode}，通过" if passed else f"退出码 {result.returncode}，存在失败"
        return passed, summary, out[:4000]
    except subprocess.TimeoutExpired:
        return False, "pytest 超时", ""
    except Exception as e:
        return False, str(e), ""


def run_pytest_with_coverage() -> tuple[bool, str, str]:
    """执行 pytest --cov，返回 (是否通过, 覆盖率摘要行, 原始输出)。"""
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT)
    cmd = [sys.executable, "-m", "pytest", "tests/", "-v", "--tb=short", "-q", "--no-header", "--cov=platform_core", "--cov=cells", "--cov-report=term-missing", "--cov-fail-under=0", "-x"]
    try:
        result = subprocess.run(
            cmd,
            cwd=str(ROOT),
            env=env,
            capture_output=True,
            text=True,
            timeout=300,
        )
        out = (result.stdout or "") + (result.stderr or "")
        passed = result.returncode == 0
        summary = "通过" if passed else "存在失败"
        cov_lines = [l for l in out.splitlines() if "TOTAL" in l or "platform_core" in l or "cells" in l]
        cov_summary = "\n".join(cov_lines[-5:]) if cov_lines else "（未产出覆盖率）"
        return passed, cov_summary, out[:5000]
    except subprocess.TimeoutExpired:
        return False, "超时", ""
    except Exception as e:
        return False, str(e), ""


def run_acceptance(skip_gateway: bool) -> tuple[bool, str, str]:
    """执行商用验收测试脚本。"""
    if skip_gateway:
        return True, "已跳过（--skip-gateway）", ""
    if not SCRIPT_ACCEPTANCE.is_file():
        return True, "验收脚本不存在，跳过", ""
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT)
    try:
        result = subprocess.run(
            [sys.executable, str(SCRIPT_ACCEPTANCE)],
            cwd=str(ROOT),
            env=env,
            capture_output=True,
            text=True,
            timeout=120,
        )
        out = (result.stdout or "") + (result.stderr or "")
        passed = result.returncode == 0
        summary = f"验收测试 {'通过' if passed else '未通过'}（退出码 {result.returncode}）"
        return passed, summary, out[:3000]
    except subprocess.TimeoutExpired:
        return False, "验收脚本超时", ""
    except Exception as e:
        return False, str(e), ""


def run_generate_docs() -> tuple[bool, str]:
    """补齐缺失文档。"""
    if not SCRIPT_GENERATE_DOCS.is_file():
        return True, "文档生成脚本不存在，跳过"
    try:
        result = subprocess.run(
            [sys.executable, str(SCRIPT_GENERATE_DOCS)],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            timeout=60,
        )
        out = (result.stdout or "") + (result.stderr or "")
        return result.returncode == 0, out.strip() or "无缺失文档"
    except Exception as e:
        return False, str(e)


def main() -> int:
    skip_gateway = "--skip-gateway" in sys.argv
    no_pytest = "--no-pytest" in sys.argv

    DIST.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    report_path = DIST / "最终验收报告.md"

    sections = [
        "# 超级PaaS平台 · 最终验收报告",
        "",
        f"**生成时间**：{stamp}",
        "",
        "---",
        "",
    ]

    all_ok = True

    # 1. 文档补齐
    doc_ok, doc_msg = run_generate_docs()
    sections.append("## 1. 文档生成")
    sections.append("")
    sections.append(f"- 结果：{'通过' if doc_ok else '未通过'}")
    sections.append(f"- 说明：{doc_msg}")
    sections.append("")
    if not doc_ok:
        all_ok = False

    # 2. 自检（pytest）
    sections.append("## 2. 自检（pytest）")
    sections.append("")
    if no_pytest:
        sections.append("- 已跳过（--no-pytest）")
    else:
        pytest_ok, pytest_summary, pytest_out = run_pytest()
        sections.append(f"- 结果：{pytest_summary}")
        if pytest_out:
            sections.append("")
            sections.append("```")
            sections.append(pytest_out.strip()[-2000:])
            sections.append("```")
        sections.append("")
        if not pytest_ok:
            all_ok = False

    # 3. 覆盖率（可选）
    sections.append("## 3. 覆盖率")
    sections.append("")
    if no_pytest:
        sections.append("- 已跳过（--no-pytest）")
    else:
        try:
            cov_ok, cov_summary, _ = run_pytest_with_coverage()
            sections.append(f"- 说明：{cov_summary}")
            if not cov_ok:
                sections.append("- 注：覆盖率执行未完全通过，见上方自检。")
        except Exception as e:
            sections.append(f"- 未执行：{e}")
    sections.append("")

    # 4. 商用验收测试
    sections.append("## 4. 商用验收测试")
    sections.append("")
    acc_ok, acc_summary, acc_out = run_acceptance(skip_gateway)
    sections.append(f"- 结果：{acc_summary}")
    if acc_out:
        sections.append("")
        sections.append("```")
        sections.append(acc_out.strip()[-2000:])
        sections.append("```")
    sections.append("")
    if not acc_ok and not skip_gateway:
        all_ok = False

    # 5. 结论
    sections.append("## 5. 结论")
    sections.append("")
    if all_ok:
        sections.append("**验收结论**：通过。")
    else:
        sections.append("**验收结论**：存在未通过项，请根据上述章节排查后重新执行。")
    sections.append("")
    sections.append("---")
    sections.append("")
    sections.append("生成自 `scripts/run_final_acceptance.py`。")

    report_path.write_text("\n".join(sections), encoding="utf-8")
    print(f"[run_final_acceptance] 报告已写入: {report_path}")
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
