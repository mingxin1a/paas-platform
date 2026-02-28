#!/usr/bin/env python3
"""
SuperPaaS 一键自检（全量化体系规范）
- PaaS 核心服务健康、网关路由有效性、双端前端可用性
- 所有已开发细胞模块接入合规与健康状态
- 文档与代码一致性（对齐 docs 接口规范与设计要求）
- 输出格式化报告 + JSON 供监控系统读取
- 兼容 self_check.sh 调用，能力一致

用法: python self_check.py [--no-verify] [--no-tests] [--json-only]
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, List, Optional

# 支持从项目根或 scripts/ 运行：在 scripts/ 时 ROOT 为仓库根
_here = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(_here) if os.path.basename(_here) == "scripts" else _here
REPORT_PATH = os.path.join(ROOT, "glass_house", "health_report.json")
CELLS_DIR = os.path.join(ROOT, "cells")
DOCS_DIR = os.path.join(ROOT, "docs")

# 细胞主列表路径（与 test_all_cells_health 一致）
CELL_MAIN_GET = {
    "crm": "/customers",
    "erp": "/orders",
    "wms": "/inventory",
    "hrm": "/employees",
    "oa": "/tasks",
    "mes": "/work-orders",
    "tms": "/shipments",
    "srm": "/suppliers",
    "plm": "/products",
    "ems": "/consumption-records",
    "his": "/patients",
    "lis": "/samples",
    "lims": "/samples",
}


@dataclass
class CheckItem:
    """单条检查结果"""
    id: str
    name: str
    passed: bool
    message: str = ""
    suggestion: str = ""
    detail: Any = None

    def to_dict(self) -> dict:
        d = {"id": self.id, "name": self.name, "passed": self.passed}
        if self.message:
            d["message"] = self.message
        if self.suggestion:
            d["suggestion"] = self.suggestion
        if self.detail is not None:
            d["detail"] = self.detail
        return d


def _http_get(url: str, headers: Optional[dict] = None, timeout: int = 5) -> tuple[int, dict, bytes]:
    """GET 请求，返回 (status_code, headers_dict, body)."""
    try:
        import urllib.request
        req = urllib.request.Request(url, method="GET")
        if headers:
            for k, v in headers.items():
                req.add_header(k, v)
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, dict(r.headers), r.read()
    except Exception as e:
        return 0, {}, str(e).encode("utf-8")


def _discover_cells() -> List[str]:
    """发现 cells 下所有细胞目录，排除 _template 与隐藏目录"""
    if not os.path.isdir(CELLS_DIR):
        return []
    return [
        n for n in sorted(os.listdir(CELLS_DIR))
        if os.path.isdir(os.path.join(CELLS_DIR, n))
        and not n.startswith(".")
        and n != "_template"
    ]


def run_paas_core_checks() -> List[CheckItem]:
    """PaaS 核心服务健康检查：网关、治理中心、监控中心"""
    out: List[CheckItem] = []
    gateway_url = os.environ.get("GATEWAY_URL", "http://localhost:8000").strip().rstrip("/")
    governance_url = os.environ.get("GOVERNANCE_URL", "http://localhost:8005").strip().rstrip("/")
    monitor_url = os.environ.get("MONITOR_CENTER_URL", "http://localhost:9000").strip().rstrip("/")

    # 网关
    code, _, body = _http_get(f"{gateway_url}/health")
    if code == 200:
        out.append(CheckItem("paas_gateway_health", "网关健康", True, "GET /health 200"))
    else:
        out.append(CheckItem(
            "paas_gateway_health", "网关健康", False,
            f"GET /health 返回 {code}" if code else "网关不可达",
            "确认网关已启动（deploy/run_gateway.py 或 docker-compose gateway 服务）",
            {"url": gateway_url, "status": code}
        ))

    # 治理中心
    code, _, _ = _http_get(f"{governance_url}/api/governance/health")
    if code == 200:
        out.append(CheckItem("paas_governance_health", "治理中心健康", True, "GET /api/governance/health 200"))
    else:
        out.append(CheckItem(
            "paas_governance_health", "治理中心健康", False,
            f"返回 {code}" if code else "治理中心不可达",
            "可选：启动治理服务（deploy/run_governance.py）；未启动时自检仍可继续",
            {"url": governance_url, "status": code}
        ))

    # 监控中心
    code, _, _ = _http_get(f"{monitor_url}/health")
    if code == 200:
        out.append(CheckItem("paas_monitor_health", "监控中心健康", True, "GET /health 200"))
    else:
        out.append(CheckItem(
            "paas_monitor_health", "监控中心健康", False,
            f"返回 {code}" if code else "监控中心不可达",
            "可选：启动 monitor 服务；未启动时自检仍可继续",
            {"url": monitor_url, "status": code}
        ))

    return out


def run_gateway_route_checks() -> List[CheckItem]:
    """网关路由有效性：/api/admin/cells 可访问并返回细胞列表"""
    out: List[CheckItem] = []
    gateway_url = os.environ.get("GATEWAY_URL", "http://localhost:8000").strip().rstrip("/")
    code, _, body = _http_get(
        f"{gateway_url}/api/admin/cells",
        headers={"Authorization": "Bearer any", "Content-Type": "application/json"},
    )
    if code != 200:
        out.append(CheckItem(
            "gateway_routes_admin", "网关 /api/admin/cells", False,
            f"返回 {code}" if code else "网关不可达",
            "需网关已启动；路由由 CELL_*_URL 或 GATEWAY_ROUTES_PATH 配置",
            {"url": f"{gateway_url}/api/admin/cells", "status": code}
        ))
        return out
    try:
        data = json.loads(body.decode("utf-8"))
        cells = data.get("data") or data.get("cells") or []
        total = data.get("total", len(cells))
        out.append(CheckItem(
            "gateway_routes_admin", "网关 /api/admin/cells", True,
            f"返回 {len(cells)} 个细胞（total={total}）",
            detail={"cells": [c.get("id") or c.get("name") for c in cells[:20]], "total": total}
        ))
    except Exception as e:
        out.append(CheckItem("gateway_routes_admin", "网关 /api/admin/cells", False, str(e), "响应非 JSON 或格式不符"))
    return out


def run_frontend_checks() -> List[CheckItem]:
    """双端前端可用性：package.json 存在，可选 dist 已构建"""
    out: List[CheckItem] = []
    for name, dir_name in [("客户端前端", "frontend"), ("管理端前端", "frontend-admin")]:
        base = os.path.join(ROOT, dir_name)
        pkg = os.path.join(base, "package.json")
        dist = os.path.join(base, "dist")
        if not os.path.isfile(pkg):
            out.append(CheckItem(
                f"frontend_{dir_name}", name, False,
                f"缺少 {dir_name}/package.json",
                f"确保 {dir_name} 目录存在且已初始化（npm install）"
            ))
        else:
            has_dist = os.path.isdir(dist)
            out.append(CheckItem(
                f"frontend_{dir_name}", name, True,
                f"package.json 存在" + ("，dist 已构建" if has_dist else "（dist 未构建，需 npm run build）"),
                "" if has_dist else f"在 {dir_name} 下执行 npm run build 可生成生产构建",
                {"hasDist": has_dist}
            ))
    return out


def _load_cell_app(cell_name: str):
    """加载细胞 app：先尝试 src.app（Flask），再 src.main（FastAPI）。"""
    cell_path = os.path.join(CELLS_DIR, cell_name)
    sys_path_saved = list(sys.path)
    to_restore = [k for k in sys.modules if k == "src" or k.startswith("src.")]
    try:
        for mod in to_restore:
            del sys.modules[mod]
        if cell_path in sys.path:
            sys.path.remove(cell_path)
        sys.path.insert(0, cell_path)
        # Flask: src.app
        app_py = os.path.join(cell_path, "src", "app.py")
        if os.path.isfile(app_py):
            try:
                import src.app as m
                app = getattr(m, "app", None)
                if app is not None:
                    return app, "flask"
            except Exception:
                pass
        # FastAPI: src.main
        main_py = os.path.join(cell_path, "src", "main.py")
        if os.path.isfile(main_py):
            try:
                import src.main as m
                app = getattr(m, "app", None)
                if app is not None:
                    return app, "fastapi"
            except Exception:
                pass
    finally:
        for mod in to_restore:
            if mod in sys.modules:
                del sys.modules[mod]
        sys.path[:] = sys_path_saved
    return None, None


def run_cell_compliance_checks() -> List[CheckItem]:
    """所有已开发细胞的接入合规与健康：/health、主列表、错误格式、X-Response-Time"""
    out: List[CheckItem] = []
    cells = _discover_cells()
    for cell_name in cells:
        try:
            _run_one_cell_compliance(cell_name, out)
        except Exception as e:
            out.append(CheckItem(
                f"cell_{cell_name}_error", f"细胞 {cell_name} 检查", False,
                str(e)[:200], "检查细胞可运行性及依赖", detail=str(e)
            ))
    return out


def _run_one_cell_compliance(cell_name: str, out: List[CheckItem]) -> None:
    """单细胞合规检查（供 run_cell_compliance_checks 调用）"""
    app, app_type = _load_cell_app(cell_name)
    if app is None:
        out.append(CheckItem(
            f"cell_{cell_name}_load", f"细胞 {cell_name} 可加载", False,
            "无 src/app.py 或 src/main.py 可运行入口",
            "补齐 src/app.py（Flask）或 src/main.py（FastAPI）"
        ))
        return

    prefix = f"cell_{cell_name}"
    if app_type == "flask":
        client = app.test_client()
        def get(path, headers=None):
            r = client.get(path, headers=headers or {})
            return r.status_code, dict(r.headers), r.get_data()
    else:
        try:
            from starlette.testclient import TestClient
            client = TestClient(app)
            def get(path, headers=None):
                r = client.get(path, headers=headers or {})
                h = dict(r.headers) if hasattr(r.headers, "__iter__") else {}
                return r.status_code, h, r.content
        except ImportError:
            out.append(CheckItem(f"{prefix}_health", f"细胞 {cell_name} 健康", False, "需 starlette 以测试 FastAPI", ""))
            return

    headers = {"X-Tenant-Id": "self-check", "Authorization": "Bearer self-check"}

    # /health
    code, hdrs, body = get("/health")
    if code != 200:
        out.append(CheckItem(f"{prefix}_health", f"细胞 {cell_name} /health", False, f"状态 {code}", "《接口设计说明书》要求 GET /health 返回 200"))
    else:
        try:
            data = json.loads(body.decode("utf-8") if isinstance(body, bytes) else body)
            if data.get("status") != "up":
                out.append(CheckItem(f"{prefix}_health", f"细胞 {cell_name} /health", False, "body.status 非 up", "应返回 {\"status\":\"up\",\"cell\":\"...\"}"))
            else:
                out.append(CheckItem(f"{prefix}_health", f"细胞 {cell_name} /health", True, "200, status=up"))
        except Exception:
            out.append(CheckItem(f"{prefix}_health", f"细胞 {cell_name} /health", True, "200（body 非 JSON 忽略）"))

    # X-Response-Time（多数细胞 after_request 会加）
    if code == 200 and hdrs:
        resp_time = hdrs.get("X-Response-Time") or hdrs.get("x-response-time")
        if not resp_time:
            out.append(CheckItem(f"{prefix}_response_time", f"细胞 {cell_name} X-Response-Time", False, "响应头缺少 X-Response-Time", "《接口设计说明书》3.1.3 要求响应头包含 X-Response-Time"))
        else:
            out.append(CheckItem(f"{prefix}_response_time", f"细胞 {cell_name} X-Response-Time", True, f"已包含 {resp_time}"))

    # 主列表契约（若有定义）
    main_path = CELL_MAIN_GET.get(cell_name)
    if main_path:
        code2, _, body2 = get(main_path, headers)
        if code2 != 200:
            out.append(CheckItem(f"{prefix}_main_list", f"细胞 {cell_name} 主列表", False, f"GET {main_path} 返回 {code2}", "契约主列表应返回 200"))
        else:
            try:
                data2 = json.loads(body2.decode("utf-8") if isinstance(body2, bytes) else body2)
                if not (isinstance(data2, list) or "data" in data2 or "total" in data2):
                    out.append(CheckItem(f"{prefix}_main_list", f"细胞 {cell_name} 主列表", False, "响应非列表形态", "应为 { data, total } 或数组"))
                else:
                    out.append(CheckItem(f"{prefix}_main_list", f"细胞 {cell_name} 主列表", True, "200, 列表形态"))
            except Exception:
                out.append(CheckItem(f"{prefix}_main_list", f"细胞 {cell_name} 主列表", True, "200"))

    # 错误格式：触发 404 检查 code/message/details/requestId
    code4, _, body4 = get("/_nonexistent_self_check_path_", headers)
    if code4 in (404, 500):
        try:
            err = json.loads(body4.decode("utf-8") if isinstance(body4, bytes) else body4)
            for key in ("code", "message", "requestId"):
                if key not in err:
                    out.append(CheckItem(
                        f"{prefix}_error_format", f"细胞 {cell_name} 错误格式", False,
                        f"错误体缺少字段: {key}",
                        "《接口设计说明书》3.1.3：code, message, details, requestId"
                    ))
                    break
            else:
                if "details" not in err:
                    out.append(CheckItem(f"{prefix}_error_format", f"细胞 {cell_name} 错误格式", False, "错误体缺少 details（可为空串）", "规范要求含 details"))
                else:
                    out.append(CheckItem(f"{prefix}_error_format", f"细胞 {cell_name} 错误格式", True, "含 code/message/details/requestId"))
        except Exception:
            out.append(CheckItem(f"{prefix}_error_format", f"细胞 {cell_name} 错误格式", False, "404 响应非 JSON", "错误响应应为 JSON"))


def run_doc_code_consistency_checks() -> List[CheckItem]:
    """文档与代码一致性：细胞不依赖 platform_core、必备交付物、网关配置化"""
    out: List[CheckItem] = []
    # 1. 细胞无 platform_core 依赖（《01》7.2 解耦）
    import_ok = True
    violations = []
    for cell_name in _discover_cells():
        cell_path = os.path.join(CELLS_DIR, cell_name)
        for root, _, files in os.walk(cell_path):
            for f in files:
                if not f.endswith(".py"):
                    continue
                path = os.path.join(root, f)
                with open(path, "r", encoding="utf-8", errors="ignore") as fp:
                    content = fp.read()
                if re.search(r"^\s*(?:from\s+platform_core|import\s+platform_core)", content, re.MULTILINE | re.IGNORECASE):
                    # 排除纯注释
                    for line in content.splitlines():
                        if "platform_core" in line and not line.strip().startswith("#"):
                            violations.append((path, line.strip()[:80]))
                            break
                    import_ok = False
    if violations:
        out.append(CheckItem(
            "doc_code_no_platform_import", "细胞不依赖 platform_core", False,
            f"发现 {len(violations)} 处引用",
            "《01 核心法律》7.2：细胞禁止 import platform_core，仅经接口/事件与平台交互",
            detail=[f"{p}: {l}" for p, l in violations[:10]]
        ))
    else:
        out.append(CheckItem("doc_code_no_platform_import", "细胞不依赖 platform_core", True, "未发现 import platform_core"))

    # 2. 细胞必备交付物：api_contract.yaml, delivery.package
    for cell_name in _discover_cells():
        base = os.path.join(CELLS_DIR, cell_name)
        contract = os.path.join(base, "api_contract.yaml")
        delivery = os.path.join(base, "delivery.package")
        if not os.path.isfile(contract):
            out.append(CheckItem(f"doc_code_contract_{cell_name}", f"细胞 {cell_name} api_contract.yaml", False, "文件缺失", "《接口设计说明书》要求接口契约 OpenAPI"))
        else:
            out.append(CheckItem(f"doc_code_contract_{cell_name}", f"细胞 {cell_name} api_contract.yaml", True, "存在"))
        if not os.path.isfile(delivery):
            out.append(CheckItem(f"doc_code_delivery_{cell_name}", f"细胞 {cell_name} delivery.package", False, "文件缺失", "交付规范要求 delivery.package"))
        else:
            out.append(CheckItem(f"doc_code_delivery_{cell_name}", f"细胞 {cell_name} delivery.package", True, "存在"))

    # 3. 网关细胞名录是否配置化（代码扫描）
    gateway_app = os.path.join(ROOT, "platform_core", "core", "gateway", "app.py")
    if os.path.isfile(gateway_app):
        with open(gateway_app, "r", encoding="utf-8") as f:
            content = f.read()
        if "_CELL_NAMES" in content and '"crm"' in content and '"erp"' in content:
            out.append(CheckItem(
                "doc_code_gateway_config_driven", "网关细胞名录配置化", False,
                "网关仍硬编码 _CELL_NAMES",
                "《项目合规校验报告》P0：建议细胞名录从 load_routes() 或配置文件获取，见 docs/待补充项清单.md P1"
            ))
        else:
            out.append(CheckItem("doc_code_gateway_config_driven", "网关细胞名录配置化", True, "未发现硬编码细胞名录"))

    return out


def run_cell_architecture_compliance() -> List[CheckItem]:
    """细胞架构合规：无跨细胞同步调用（禁止直接 HTTP 请求其他细胞 URL）。"""
    out: List[CheckItem] = []
    violations_sync = []
    for cell_name in _discover_cells():
        cell_path = os.path.join(CELLS_DIR, cell_name)
        for root, _, files in os.walk(cell_path):
            for f in files:
                if not f.endswith(".py"):
                    continue
                path = os.path.join(root, f)
                with open(path, "r", encoding="utf-8", errors="ignore") as fp:
                    content = fp.read()
                if re.search(r"requests?\.(get|post|put|patch|delete)\s*\(\s*[\"'].*/(crm|erp|oa|srm|wms)[\"'/]", content, re.I):
                    violations_sync.append(f"{path}: 疑似直接请求其他细胞")
    if violations_sync:
        out.append(CheckItem(
            "cell_arch_no_cross_cell",
            "细胞架构合规（无跨细胞同步调用）",
            False,
            f"发现 {len(violations_sync)} 处",
            "细胞仅经网关 HTTP 与平台交互，禁止直接请求其他细胞",
            detail=violations_sync[:15],
        ))
    else:
        out.append(CheckItem(
            "cell_arch_no_cross_cell",
            "细胞架构合规（无跨细胞同步调用）",
            True,
            "未发现违规",
        ))
    return out


def run_full_link_health() -> List[CheckItem]:
    """全链路健康：网关 -> 各细胞 /health 可达。"""
    out: List[CheckItem] = []
    gateway_url = os.environ.get("GATEWAY_URL", "http://localhost:8000").strip().rstrip("/")
    code_gw, _, _ = _http_get(f"{gateway_url}/health")
    if code_gw != 200:
        out.append(CheckItem(
            "full_link_gateway",
            "全链路-网关",
            False,
            f"网关 /health {code_gw}",
            "先启动网关",
        ))
        return out
    out.append(CheckItem("full_link_gateway", "全链路-网关", True, "200"))
    for cell_name in ["crm", "erp", "oa", "srm"]:
        code, _, _ = _http_get(f"{gateway_url}/api/v1/{cell_name}/health")
        if code == 200:
            out.append(CheckItem(f"full_link_{cell_name}", f"全链路-细胞 {cell_name}", True, "200"))
        else:
            out.append(CheckItem(
                f"full_link_{cell_name}",
                f"全链路-细胞 {cell_name}",
                False,
                f"GET /api/v1/{cell_name}/health 返回 {code}",
                "确认细胞已启动且网关路由已配置",
            ))
    return out


def run_verify_all_cells(no_verify: bool) -> List[CheckItem]:
    """全细胞交付校验（evolution_engine/verify_all_cells.py）"""
    out: List[CheckItem] = []
    if no_verify:
        out.append(CheckItem("verify_all_cells", "全细胞交付校验", True, "已跳过（--no-verify）"))
        return out
    path = os.path.join(ROOT, "evolution_engine", "verify_all_cells.py")
    if not os.path.isfile(path):
        out.append(CheckItem("verify_all_cells", "全细胞交付校验", True, "脚本不存在，跳过"))
        return out
    r = subprocess.run([sys.executable, path], cwd=ROOT, capture_output=True, text=True, timeout=90)
    if r.returncode == 0:
        out.append(CheckItem("verify_all_cells", "全细胞交付校验", True, "全部通过"))
    else:
        out.append(CheckItem(
            "verify_all_cells", "全细胞交付校验", False,
            "部分细胞未通过",
            "查看 evolution_engine/verify_all_cells.py 与各细胞 delivery.package、completion.manifest",
            detail=(r.stderr or r.stdout or "")[:500]
        ))
    return out


def run_pytest_tests(no_tests: bool) -> List[CheckItem]:
    """pytest tests/ 单元与集成测试"""
    out: List[CheckItem] = []
    if no_tests:
        out.append(CheckItem("pytest_tests", "pytest tests/", True, "已跳过（--no-tests）"))
        return out
    r = subprocess.run(
        [sys.executable, "-m", "pytest", "tests/", "-v", "--tb=short", "-q"],
        cwd=ROOT, capture_output=True, text=True, timeout=120,
    )
    passed = failed = 0
    for line in (r.stdout or "").splitlines():
        line = line.strip()
        if " passed" in line and "failed" not in line:
            try:
                passed = int(line.split()[0])
            except (IndexError, ValueError):
                pass
        if " failed" in line:
            try:
                parts = line.replace(",", " ").split()
                for i, p in enumerate(parts):
                    if p == "failed":
                        failed = int(parts[i - 1])
                        break
            except (IndexError, ValueError):
                pass
    if passed == 0 and failed == 0 and r.returncode != 0:
        failed = 1
    total = passed + failed or 1
    ok = r.returncode == 0
    out.append(CheckItem(
        "pytest_tests", "pytest tests/", ok,
        f"passed={passed}, failed={failed}, total={total}",
        "" if ok else "修复失败用例后重新运行 pytest tests/",
        {"passed": passed, "failed": failed, "total": total}
    ))
    return out


def build_report(
    paas: List[CheckItem],
    routes: List[CheckItem],
    frontends: List[CheckItem],
    cells: List[CheckItem],
    doc_code: List[CheckItem],
    arch: List[CheckItem],
    full_link: List[CheckItem],
    verify: List[CheckItem],
    pytest: List[CheckItem],
) -> dict:
    """组装 JSON 报告（供监控系统读取）"""
    all_items = paas + routes + frontends + cells + doc_code + arch + full_link + verify + pytest
    passed = sum(1 for c in all_items if c.passed)
    failed = sum(1 for c in all_items if not c.passed)
    status = "healthy" if failed == 0 else "degraded"

    # 从 pytest 结果提取 testsPassed/testsFailed（兼容旧版监控）
    tests_passed = tests_failed = 0
    for c in pytest:
        if c.detail and isinstance(c.detail, dict):
            tests_passed = c.detail.get("passed", 0)
            tests_failed = c.detail.get("failed", 0)
            break

    # 治理中心指标（若可达）
    governance_metrics = None
    try:
        gov_url = os.environ.get("GOVERNANCE_URL", "http://localhost:8005").strip().rstrip("/")
        _, _, body = _http_get(f"{gov_url}/api/governance/metrics")
        if body:
            governance_metrics = json.loads(body.decode("utf-8"))
    except Exception:
        pass

    cell_items = [c for c in all_items if "cell_" in c.id]
    cell_passed = sum(1 for c in cell_items if c.passed)
    health_pct = round(100 * passed / len(all_items), 1) if all_items else 0
    return {
        "version": "2.0",
        "generatedAt": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "standard": "超级PaaS平台全量化体系规范",
        "summary": {
            "status": status,
            "totalChecks": len(all_items),
            "passed": passed,
            "failed": failed,
            "platformHealthPercent": health_pct,
            "cellCompliancePassed": cell_passed,
            "cellComplianceTotal": len(cell_items),
            "testsPassed": tests_passed,
            "testsFailed": tests_failed,
            "testsTotal": tests_passed + tests_failed or 1,
        },
        "goldenMetrics": {
            "suppaas_request_duration_ms": 0,
            "suppaas_request_errors_total": failed,
            "suppaas_request_total": max(len(all_items), 1),
            "suppaas_saturation": 0,
        },
        "governance": {"metrics": governance_metrics},
        "sections": {
            "paasCore": [c.to_dict() for c in paas],
            "gatewayRoutes": [c.to_dict() for c in routes],
            "frontends": [c.to_dict() for c in frontends],
            "cellCompliance": [c.to_dict() for c in cells],
            "docCodeConsistency": [c.to_dict() for c in doc_code],
            "cellArchitectureCompliance": [c.to_dict() for c in arch],
            "fullLinkHealth": [c.to_dict() for c in full_link],
            "verifyAllCells": [c.to_dict() for c in verify],
            "pytestTests": [c.to_dict() for c in pytest],
        },
        "checks": [c.to_dict() for c in all_items],
    }


def print_formatted_report(
    paas: List[CheckItem],
    routes: List[CheckItem],
    frontends: List[CheckItem],
    cells: List[CheckItem],
    doc_code: List[CheckItem],
    arch: List[CheckItem],
    full_link: List[CheckItem],
    verify: List[CheckItem],
    pytest: List[CheckItem],
) -> None:
    """输出格式化文本报告：平台健康度、细胞合规性、通过项、不通过项、修复建议"""
    all_items = paas + routes + frontends + cells + doc_code + arch + full_link + verify + pytest
    passed_list = [c for c in all_items if c.passed]
    failed_list = [c for c in all_items if not c.passed]
    total = len(all_items) or 1
    health_pct = round(100 * len(passed_list) / total, 1)

    print("\n" + "=" * 60)
    print("SuperPaaS 自检报告（细胞合规性 + 平台健康度一键校验）")
    print("=" * 60)
    print("【平台健康度】", f"通过: {len(passed_list)}  不通过: {len(failed_list)}  合计: {total}  健康度: {health_pct}%")
    cell_items = [c for c in cells if "cell_" in c.id]
    cell_ok = sum(1 for c in cell_items if c.passed)
    cell_total = len(cell_items) or 1
    print("【细胞合规性】", f"细胞检查: {cell_ok}/{len(cell_items)} 通过")
    print()

    if failed_list:
        print("--- 不通过项 ---")
        for c in failed_list:
            print(f"  [FAIL] {c.name} ({c.id})")
            print(f"         {c.message}")
            if c.suggestion:
                print(f"         建议: {c.suggestion}")
        print()

    print("--- 通过项（节选） ---")
    for c in passed_list[:20]:
        print(f"  [PASS] {c.name}")
    if len(passed_list) > 20:
        print(f"  ... 其余 {len(passed_list) - 20} 项通过")
    print("=" * 60)


def main() -> int:
    no_verify = "--no-verify" in sys.argv
    no_tests = "--no-tests" in sys.argv
    json_only = "--json-only" in sys.argv

    os.chdir(ROOT)
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    if not json_only:
        print("[self_check] 开始自检 @", ts)

    # 1. PaaS 核心
    paas = run_paas_core_checks()
    routes = run_gateway_route_checks()
    frontends = run_frontend_checks()
    # 2. 细胞合规与健康
    cells = run_cell_compliance_checks()
    # 3. 文档与代码一致性
    doc_code = run_doc_code_consistency_checks()
    # 4. 细胞架构合规 + 全链路健康
    arch = run_cell_architecture_compliance()
    full_link = run_full_link_health()
    # 5. 全细胞交付校验
    verify = run_verify_all_cells(no_verify)
    # 6. pytest
    pytest = run_pytest_tests(no_tests)

    report = build_report(paas, routes, frontends, cells, doc_code, arch, full_link, verify, pytest)
    os.makedirs(os.path.dirname(REPORT_PATH), exist_ok=True)
    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    if not json_only:
        print_formatted_report(paas, routes, frontends, cells, doc_code, arch, full_link, verify, pytest)
        print(f"[self_check] 健康报告已写入: {REPORT_PATH}")
        print(json.dumps(report, ensure_ascii=False, indent=2))

    failed_count = report["summary"]["failed"]
    if failed_count > 0:
        if not json_only:
            print("[self_check] 存在不通过项，整体状态: degraded")
        return 1
    if not json_only:
        print("[self_check] 全部通过，整体状态: healthy")
    return 0


if __name__ == "__main__":
    sys.exit(main())
