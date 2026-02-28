#!/usr/bin/env python3
"""
PaaS 平台全量交付验证脚本

覆盖：环境一致性检查、PaaS 核心层合规检查、细胞模块接入校验、接口规范验证、
      权限安全校验、冒烟测试。每环节不通过即终止并输出错误原因。
依据：docs/整体检验程序说明、docs/细胞模块接入校验报告、docs/架构实现对照表、
      《接口设计说明书》《01_核心法律》、顶层架构设计。

用法:
  python scripts/run_full_verification.py                    # 全量验证
  python scripts/run_full_verification.py --no-verify        # 跳过交付校验
  python scripts/run_full_verification.py --no-tests         # 跳过 pytest 接口规范
  python scripts/run_full_verification.py --no-smoke         # 跳过冒烟（无需网关）
  python scripts/run_full_verification.py --report PATH      # 指定 HTML 报告路径

退出码: 0 全部通过, 1 某环节不通过（已写入 HTML 报告）
"""
from __future__ import annotations

import os
import re
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List, Optional

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CELLS_DIR = os.path.join(ROOT, "cells")
PLATFORM_CORE_DIR = os.path.join(ROOT, "platform_core")
DOCS_DIR = os.path.join(ROOT, "docs")
EVOLUTION_ENGINE_DIR = os.path.join(ROOT, "evolution_engine")
DEPLOY_DIR = os.path.join(ROOT, "deploy")
TESTS_DIR = os.path.join(ROOT, "tests")
DEFAULT_REPORT_PATH = os.path.join(ROOT, "glass_house", "delivery_verification_report.html")

# 交付规范依据（用于报告）
REFERENCE_DOCS = [
    "《整体检验程序说明》",
    "《细胞模块接入校验报告》",
    "《架构实现对照表》",
    "《接口设计说明书》",
    "《01_核心法律》",
    "《超级PaaS平台全量化系统架构设计说明书》",
]


@dataclass
class StepResult:
    """单环节校验结果"""
    step_id: str
    name: str
    passed: bool
    message: str = ""
    detail: str = ""
    criteria: str = ""  # 通过/不通过标准说明


def _discover_cells(exclude_template: bool = True) -> List[str]:
    """发现 cells 下业务细胞目录，可选排除 _template。"""
    if not os.path.isdir(CELLS_DIR):
        return []
    names = [
        n for n in sorted(os.listdir(CELLS_DIR))
        if os.path.isdir(os.path.join(CELLS_DIR, n)) and not n.startswith(".")
    ]
    if exclude_template and "_template" in names:
        names = [n for n in names if n != "_template"]
    return names


# ---------- 1. 环境一致性检查 ----------
def run_env_consistency() -> StepResult:
    """环境一致性：项目根目录、必备目录、Python 版本。"""
    criteria = "项目根目录存在；cells/、platform_core/、evolution_engine/、docs/、deploy/、tests/ 存在；Python 3.7+。"
    if not os.path.isdir(ROOT):
        return StepResult("env_consistency", "环境一致性检查", False,
            "项目根目录不存在", str(ROOT), criteria)
    required_dirs = ["cells", "platform_core", "evolution_engine", "docs", "deploy", "tests"]
    missing = [d for d in required_dirs if not os.path.isdir(os.path.join(ROOT, d))]
    if missing:
        return StepResult("env_consistency", "环境一致性检查", False,
            f"缺少必备目录: {', '.join(missing)}", "", criteria)
    ver = sys.version_info
    if ver.major < 3 or (ver.major == 3 and ver.minor < 7):
        return StepResult("env_consistency", "环境一致性检查", False,
            f"需要 Python 3.7+，当前 {ver.major}.{ver.minor}", "", criteria)
    cells = _discover_cells()
    if not cells:
        return StepResult("env_consistency", "环境一致性检查", False,
            "cells/ 下未发现任何业务细胞目录", "", criteria)
    return StepResult("env_consistency", "环境一致性检查", True,
        f"根目录与必备目录完整，Python {ver.major}.{ver.minor}，发现 {len(cells)} 个细胞", "", criteria)


# ---------- 2. PaaS 核心层合规检查 ----------
def run_paas_core_compliance() -> StepResult:
    """PaaS 核心层合规：platform_core 结构、架构解耦（细胞不 import platform_core）。"""
    criteria = "platform_core/core/gateway、core/governance 存在；细胞代码中禁止 import platform_core（《01_核心法律》7.2）。"
    gateway_dir = os.path.join(PLATFORM_CORE_DIR, "core", "gateway")
    governance_dir = os.path.join(PLATFORM_CORE_DIR, "core", "governance")
    if not os.path.isdir(gateway_dir):
        return StepResult("paas_core", "PaaS 核心层合规检查", False,
            "platform_core/core/gateway 不存在", "", criteria)
    if not os.path.isdir(governance_dir):
        return StepResult("paas_core", "PaaS 核心层合规检查", False,
            "platform_core/core/governance 不存在", "", criteria)
    # 架构解耦：细胞不得 import platform_core
    pattern = re.compile(
        r"^\s*(?:from\s+platform_core|import\s+platform_core)",
        re.IGNORECASE | re.MULTILINE,
    )
    violations = []
    for cell_name in _discover_cells():
        cell_path = os.path.join(CELLS_DIR, cell_name)
        for root, _, files in os.walk(cell_path):
            for f in files:
                if not f.endswith(".py"):
                    continue
                path = os.path.join(root, f)
                try:
                    with open(path, "r", encoding="utf-8", errors="ignore") as fp:
                        content = fp.read()
                except Exception:
                    continue
                for m in pattern.finditer(content):
                    line_start = content.rfind("\n", 0, m.start()) + 1
                    line_end = content.find("\n", m.start())
                    if line_end == -1:
                        line_end = len(content)
                    line = content[line_start:line_end].strip()
                    if line.startswith("#"):
                        continue
                    rel = os.path.relpath(path, ROOT)
                    violations.append(f"{rel}: {line[:80]}")
    if violations:
        return StepResult("paas_core", "PaaS 核心层合规检查", False,
            f"细胞中存在 {len(violations)} 处对 platform_core 的引用，违反架构解耦",
            "\n".join(violations[:15]), criteria)
    return StepResult("paas_core", "PaaS 核心层合规检查", True,
        "平台核心目录完整，细胞无 platform_core 依赖", "", criteria)


# ---------- 3. 细胞模块接入校验 ----------
def run_cell_delivery_verification(no_verify: bool) -> StepResult:
    """细胞模块接入校验：全细胞 delivery.package、completion.manifest、cell_profile、api_contract、auto_healing、src/app.py。"""
    criteria = "每个细胞具备 delivery.package、completion.manifest、cell_profile.md、api_contract.yaml、auto_healing.yaml、src/app.py（《整体检验程序说明》§3）。"
    if no_verify:
        return StepResult("cell_delivery", "细胞模块接入校验", True, "已跳过（--no-verify）", "", criteria)
    script = os.path.join(ROOT, "evolution_engine", "verify_all_cells.py")
    if not os.path.isfile(script):
        return StepResult("cell_delivery", "细胞模块接入校验", False,
            "evolution_engine/verify_all_cells.py 不存在", "", criteria)
    r = subprocess.run(
        [sys.executable, script],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=120,
    )
    if r.returncode == 0:
        return StepResult("cell_delivery", "细胞模块接入校验", True, "全细胞交付校验通过", "", criteria)
    stderr = (r.stderr or "").strip()
    stdout = (r.stdout or "").strip()
    detail = stderr or stdout or "verify_all_cells 返回非零"
    return StepResult("cell_delivery", "细胞模块接入校验", False,
        "部分细胞未通过交付校验（delivery.package/completion.manifest/cell_profile/api_contract/auto_healing/src/app.py）",
        detail[:2000], criteria)


# ---------- 4. 接口规范验证 ----------
def run_interface_spec_verification(no_tests: bool) -> StepResult:
    """接口规范验证：每细胞 /health、主列表契约、错误格式、X-Response-Time（通过 pytest test_all_cells_health + 架构解耦测试）。"""
    criteria = "每细胞 GET /health 返回 200 且 status=up、cell=名；主列表 GET 返回 200 且列表形态；《接口设计说明书》3.1.3 统一错误格式与 X-Response-Time。"
    if no_tests:
        return StepResult("interface_spec", "接口规范验证", True, "已跳过（--no-tests）", "", criteria)
    # 架构解耦测试
    decouple = os.path.join(TESTS_DIR, "test_architecture_decoupling.py")
    if os.path.isfile(decouple):
        r = subprocess.run(
            [sys.executable, "-m", "pytest", decouple, "-v", "--tb=short", "-q"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=60,
        )
        if r.returncode != 0:
            out = (r.stdout or "") + (r.stderr or "")
            return StepResult("interface_spec", "接口规范验证", False,
                "架构解耦校验未通过（细胞不得依赖 platform_core）",
                out[-1500:] if len(out) > 1500 else out, criteria)
    # 全细胞健康与契约
    health_test = os.path.join(TESTS_DIR, "test_all_cells_health.py")
    if not os.path.isfile(health_test):
        return StepResult("interface_spec", "接口规范验证", False,
            "tests/test_all_cells_health.py 不存在", "", criteria)
    r = subprocess.run(
        [sys.executable, "-m", "pytest", health_test, "-v", "--tb=short", "-q"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=120,
    )
    if r.returncode != 0:
        out = (r.stdout or "") + (r.stderr or "")
        return StepResult("interface_spec", "接口规范验证", False,
            "部分细胞健康或契约主列表校验未通过",
            out[-2000:] if len(out) > 2000 else out, criteria)
    return StepResult("interface_spec", "接口规范验证", True,
        "架构解耦与全细胞健康/契约校验通过", "", criteria)


# ---------- 5. 权限安全校验 ----------
def run_permission_security_check() -> StepResult:
    """权限安全校验：网关健康、/api/admin/cells 可访问（带 Authorization 时 200 或合规 401）。"""
    criteria = "网关 GET /health 返回 200；/api/admin/cells 可访问（带 Authorization 头），用于路由与细胞发现。"
    gateway_url = os.environ.get("GATEWAY_URL", "http://localhost:8000").strip().rstrip("/")
    try:
        import urllib.request
        req = urllib.request.Request(f"{gateway_url}/health", method="GET")
        with urllib.request.urlopen(req, timeout=5) as r:
            if r.status != 200:
                return StepResult("permission_security", "权限安全校验", False,
                    f"网关 /health 返回 {r.status}", "", criteria)
    except Exception as e:
        return StepResult("permission_security", "权限安全校验", False,
            "网关不可达，无法执行权限安全校验（请先启动网关：deploy/run_gateway.py 或 docker-compose）",
            str(e), criteria)
    try:
        import urllib.request
        req = urllib.request.Request(
            f"{gateway_url}/api/admin/cells",
            method="GET",
            headers={"Authorization": "Bearer delivery-verification", "Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=5) as r:
            body = r.read().decode("utf-8", errors="ignore")
            if r.status == 200:
                try:
                    import json
                    data = json.loads(body)
                    cells = data.get("data") or data.get("cells") or []
                    return StepResult("permission_security", "权限安全校验", True,
                        f"网关健康，/api/admin/cells 返回 200，细胞数 {len(cells)}", "", criteria)
                except Exception:
                    return StepResult("permission_security", "权限安全校验", True,
                        "网关健康，/api/admin/cells 返回 200", "", criteria)
            # 401 视为网关已做鉴权校验，也通过
            if r.status == 401:
                return StepResult("permission_security", "权限安全校验", True,
                    "网关健康，/api/admin/cells 需鉴权（401），符合安全要求", "", criteria)
            return StepResult("permission_security", "权限安全校验", False,
                f"/api/admin/cells 返回 {r.status}", body[:500], criteria)
    except Exception as e:
        return StepResult("permission_security", "权限安全校验", False,
            "访问 /api/admin/cells 失败", str(e), criteria)


# ---------- 6. 冒烟测试 ----------
def run_smoke_test(no_smoke: bool) -> StepResult:
    """冒烟测试：对已部署网关执行健康与细胞接口检查。"""
    criteria = "网关已启动；冒烟脚本对网关 /health 及配置的细胞路径 GET 返回 200（《整体检验程序说明》§2.4）。"
    if no_smoke:
        return StepResult("smoke_test", "冒烟测试", True, "已跳过（--no-smoke）", "", criteria)
    script = os.path.join(DEPLOY_DIR, "smoke_test.py")
    if not os.path.isfile(script):
        return StepResult("smoke_test", "冒烟测试", False, "deploy/smoke_test.py 不存在", "", criteria)
    r = subprocess.run(
        [sys.executable, script],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=90,
        env={**os.environ},
    )
    if r.returncode == 0:
        return StepResult("smoke_test", "冒烟测试", True, "冒烟测试全部通过", "", criteria)
    stderr = (r.stderr or "").strip()
    stdout = (r.stdout or "").strip()
    return StepResult("smoke_test", "冒烟测试", False,
        "冒烟测试未通过（网关或细胞路径不可用）",
        (stderr or stdout)[:2000], criteria)


def write_html_report(results: List[StepResult], report_path: str, overall_pass: bool) -> None:
    """生成 HTML 格式验证报告，可直接用于交付验收。"""
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    title = "PaaS 平台全量交付验证报告"
    status_text = "通过" if overall_pass else "不通过"
    status_class = "pass" if overall_pass else "fail"

    rows = []
    for r in results:
        row_class = "pass" if r.passed else "fail"
        status_cell = "通过" if r.passed else "不通过"
        detail_html = f"<pre>{_escape(r.detail)}</pre>" if r.detail else ""
        criteria_html = f"<p class=\"criteria\">标准：{_escape(r.criteria)}</p>" if r.criteria else ""
        rows.append(f"""
        <tr class="{row_class}">
          <td>{_escape(r.name)}</td>
          <td><span class="badge {row_class}">{status_cell}</span></td>
          <td>{_escape(r.message)}</td>
          <td>{detail_html}{criteria_html}</td>
        </tr>""")

    refs = "；".join(REFERENCE_DOCS)
    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{title}</title>
  <style>
    :root {{ --pass: #0d6b0d; --fail: #b00; --bg: #f8f9fa; }}
    body {{ font-family: "Segoe UI", "PingFang SC", sans-serif; margin: 0; padding: 24px; background: var(--bg); }}
    .container {{ max-width: 900px; margin: 0 auto; background: #fff; padding: 32px; box-shadow: 0 2px 8px rgba(0,0,0,.08); border-radius: 8px; }}
    h1 {{ margin: 0 0 8px; font-size: 1.5rem; color: #1a1a1a; }}
    .meta {{ color: #666; font-size: 0.9rem; margin-bottom: 24px; }}
    .summary {{ font-size: 1.1rem; margin-bottom: 24px; padding: 12px 16px; border-radius: 6px; }}
    .summary.pass {{ background: #e6f4ea; color: var(--pass); }}
    .summary.fail {{ background: #fdecea; color: var(--fail); }}
    table {{ width: 100%; border-collapse: collapse; }}
    th, td {{ padding: 10px 12px; text-align: left; border-bottom: 1px solid #eee; vertical-align: top; }}
    th {{ background: #f0f0f0; font-weight: 600; }}
    td pre {{ margin: 0; font-size: 0.85rem; white-space: pre-wrap; word-break: break-all; max-height: 200px; overflow: auto; }}
    .badge {{ display: inline-block; padding: 2px 8px; border-radius: 4px; font-size: 0.85rem; }}
    .badge.pass {{ background: #e6f4ea; color: var(--pass); }}
    .badge.fail {{ background: #fdecea; color: var(--fail); }}
    .criteria {{ margin: 4px 0 0; font-size: 0.85rem; color: #555; }}
    .footer {{ margin-top: 24px; padding-top: 16px; border-top: 1px solid #eee; font-size: 0.85rem; color: #666; }}
  </style>
</head>
<body>
  <div class="container">
    <h1>{title}</h1>
    <p class="meta">验证时间：{_escape(ts)} | 项目：paas-platform | 依据：{_escape(refs)}</p>
    <div class="summary {status_class}">结论：<strong>整体验证{status_text}</strong></div>
    <table>
      <thead>
        <tr>
          <th>校验环节</th>
          <th>结果</th>
          <th>说明</th>
          <th>详情/标准</th>
        </tr>
      </thead>
      <tbody>
{"".join(rows)}
      </tbody>
    </table>
    <div class="footer">本报告由 scripts/run_full_verification.py 生成，用于交付验收。通过即表示符合顶层架构设计与交付规范。</div>
  </div>
</body>
</html>"""
    os.makedirs(os.path.dirname(report_path) or ".", exist_ok=True)
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(html)


def _escape(s: str) -> str:
    if not s:
        return ""
    return (
        s.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def main() -> int:
    no_verify = "--no-verify" in sys.argv
    no_tests = "--no-tests" in sys.argv
    no_smoke = "--no-smoke" in sys.argv
    report_path = DEFAULT_REPORT_PATH
    for i, arg in enumerate(sys.argv):
        if arg == "--report" and i + 1 < len(sys.argv):
            report_path = sys.argv[i + 1]
            break

    os.chdir(ROOT)
    results: List[StepResult] = []

    steps = [
        ("环境一致性检查", lambda: run_env_consistency()),
        ("PaaS 核心层合规检查", lambda: run_paas_core_compliance()),
        ("细胞模块接入校验", lambda: run_cell_delivery_verification(no_verify)),
        ("接口规范验证", lambda: run_interface_spec_verification(no_tests)),
        ("权限安全校验", lambda: run_permission_security_check()),
        ("冒烟测试", lambda: run_smoke_test(no_smoke)),
    ]

    for name, run_step in steps:
        result = run_step()
        results.append(result)
        if not result.passed:
            print(f"[run_full_verification] 不通过：{result.name}", file=sys.stderr)
            print(f"  {result.message}", file=sys.stderr)
            if result.detail:
                print(result.detail[:500], file=sys.stderr)
            write_html_report(results, report_path, overall_pass=False)
            print(f"[run_full_verification] 已生成报告: {report_path}", file=sys.stderr)
            return 1

    write_html_report(results, report_path, overall_pass=True)
    print(f"[run_full_verification] 全部通过，报告已生成: {report_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
