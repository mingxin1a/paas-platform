#!/usr/bin/env python3
"""
自动生成/补齐细胞文档：用户手册、管理员手册、接口文档。
根据 cells/*/src/app.py 路由生成接口文档；缺失时生成占位用户/管理员手册。
用法:
  python scripts/generate_docs.py           # 仅生成缺失文档
  python scripts/generate_docs.py --force    # 强制覆盖接口文档（从路由重新生成）
  python scripts/generate_docs.py --cell mes # 仅处理指定细胞
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CELLS_DIR = ROOT / "cells"
DOCS_CELL = ROOT / "docs" / "commercial_delivery" / "细胞"

CELL_NAMES = {
    "crm": "客户关系",
    "erp": "企业资源",
    "oa": "协同办公",
    "srm": "供应商",
    "mes": "制造执行",
    "wms": "仓储管理",
    "tms": "运输管理",
    "hrm": "人力资源",
    "ems": "能源管理",
    "plm": "产品生命周期",
    "his": "医院信息",
    "lis": "检验信息",
    "lims": "实验室",
}


def extract_routes(app_py_path: Path) -> list[tuple[str, str]]:
    """从 app.py 提取 @app.route 路径与 methods。"""
    if not app_py_path.is_file():
        return []
    text = app_py_path.read_text(encoding="utf-8")
    routes = []
    # @app.route("/path") 或 @app.route("/path", methods=["GET","POST"])
    for m in re.finditer(r'@app\.route\s*\(\s*["\']([^"\']+)["\']\s*(?:,\s*methods\s*=\s*\[([^\]]+)\])?\s*\)', text):
        path = m.group(1)
        methods = m.group(2)
        if methods:
            methods = re.sub(r'["\']', "", methods).strip()
        else:
            methods = "GET"
        routes.append((path, methods))
    return routes


def ensure_interface_doc(cell_id: str, cell_name: str, routes: list[tuple[str, str]], force: bool) -> bool:
    """生成或更新接口文档（商用版）。"""
    doc_dir = DOCS_CELL / cell_id.upper()
    doc_dir.mkdir(parents=True, exist_ok=True)
    fname = f"{cell_id.upper()}接口文档（商用版）.md"
    path = doc_dir / fname
    if path.exists() and not force:
        return False
    lines = [
        f"# {cell_name} 接口文档（商用版）",
        "",
        f"**版本**：1.0 | **细胞**：{cell_id.upper()}",
        "",
        "## 访问说明",
        "",
        f"- 经网关：`/api/v1/{cell_id}/<path>`",
        "- 请求头：`Authorization`、`X-Tenant-Id`、`X-Request-ID`",
        "",
        "## 路由列表",
        "",
        "| 路径 | 方法 | 说明 |",
        "|------|------|------|",
    ]
    for p, m in routes:
        lines.append(f"| {p} | {m} | — |")
    lines.extend(["", "---", "由 `scripts/generate_docs.py` 根据 app.py 自动生成。"])
    path.write_text("\n".join(lines), encoding="utf-8")
    return True


def ensure_user_manual(cell_id: str, cell_name: str) -> bool:
    """缺失时生成用户操作手册占位。"""
    doc_dir = DOCS_CELL / cell_id.upper()
    doc_dir.mkdir(parents=True, exist_ok=True)
    fname = f"{cell_id.upper()}用户操作手册.md"
    path = doc_dir / fname
    if path.exists():
        return False
    path.write_text(
        f"# {cell_name} 用户操作手册\n\n"
        f"**版本**：1.0 | **细胞**：{cell_id.upper()}\n\n"
        "## 1. 概述\n\n"
        f"本文档面向使用 {cell_name} 模块的最终用户，说明常用操作流程。\n\n"
        "## 2. 功能入口\n\n"
        "- 登录后从主导航进入对应模块。\n"
        "- 列表支持分页、筛选与导出。\n\n"
        "## 3. 操作说明\n\n"
        "（请根据实际功能补充：新建、编辑、审批、导出等步骤。）\n\n"
        "---\n"
        "由 `scripts/generate_docs.py` 自动生成占位，需人工补充。\n",
        encoding="utf-8",
    )
    return True


def ensure_admin_manual(cell_id: str, cell_name: str) -> bool:
    """缺失时生成管理员手册占位。"""
    doc_dir = DOCS_CELL / cell_id.upper()
    doc_dir.mkdir(parents=True, exist_ok=True)
    fname = f"{cell_id.upper()}管理员手册.md"
    path = doc_dir / fname
    if path.exists():
        return False
    path.write_text(
        f"# {cell_name} 管理员手册\n\n"
        f"**版本**：1.0 | **细胞**：{cell_id.upper()}\n\n"
        "## 1. 权限与角色\n\n"
        "（说明本模块涉及的角色与数据权限。）\n\n"
        "## 2. 系统参数\n\n"
        "（说明环境变量、配置项、留存策略等。）\n\n"
        "## 3. 故障处理\n\n"
        "（常见问题与排查步骤。）\n\n"
        "---\n"
        "由 `scripts/generate_docs.py` 自动生成占位，需人工补充。\n",
        encoding="utf-8",
    )
    return True


def main() -> int:
    force = "--force" in sys.argv
    cell_filter = None
    for i, a in enumerate(sys.argv):
        if a == "--cell" and i + 1 < len(sys.argv):
            cell_filter = sys.argv[i + 1].strip().lower()
            break

    if not CELLS_DIR.is_dir():
        print("cells 目录不存在")
        return 1

    generated = []
    cells = [d.name.lower() for d in CELLS_DIR.iterdir() if d.is_dir() and not d.name.startswith("_")]
    if cell_filter:
        cells = [c for c in cells if c == cell_filter]
    for cell_id in sorted(cells):
        if cell_id not in CELL_NAMES:
            continue
        cell_name = CELL_NAMES[cell_id]
        app_py = CELLS_DIR / cell_id / "src" / "app.py"
        routes = extract_routes(app_py)
        if ensure_interface_doc(cell_id, cell_name, routes, force):
            generated.append(f"{cell_id}: 接口文档")
        if ensure_user_manual(cell_id, cell_name):
            generated.append(f"{cell_id}: 用户操作手册")
        if ensure_admin_manual(cell_id, cell_name):
            generated.append(f"{cell_id}: 管理员手册")

    if generated:
        print("已生成/更新：", ", ".join(generated))
    else:
        print("无缺失文档；使用 --force 可强制重新生成接口文档。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
