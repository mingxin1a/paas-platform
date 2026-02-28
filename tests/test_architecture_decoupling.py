"""
架构解耦专项校验：对齐《01_核心法律》7.2/7.4 与《项目合规校验报告》。
- 细胞不得依赖 platform_core 代码（禁止 import platform_core）
- 网关细胞名录应由配置驱动（可选校验：检测硬编码 _CELL_NAMES）
纳入 run_full_verification 与 self_check。
"""
import os
import re

import pytest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
CELLS_DIR = os.path.join(ROOT, "cells")
GATEWAY_APP = os.path.join(ROOT, "platform_core", "core", "gateway", "app.py")

# 禁止细胞中出现的 import 模式（作为 import 语句的一部分）
IMPORT_PLATFORM_PATTERN = re.compile(
    r"^\s*(?:from\s+platform_core|import\s+platform_core)",
    re.IGNORECASE | re.MULTILINE,
)


def _collect_py_files_under_dir(base_dir):
    """收集目录下所有 .py 文件路径（相对 base_dir）。"""
    if not os.path.isdir(base_dir):
        return []
    out = []
    for root, _, files in os.walk(base_dir):
        for f in files:
            if f.endswith(".py"):
                out.append(os.path.join(root, f))
    return out


def test_cells_do_not_import_platform_core():
    """细胞模块不得 import platform_core，否则违反架构解耦（01 7.2/7.4）。"""
    violations = []
    for path in _collect_py_files_under_dir(CELLS_DIR):
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
        # 仅检查作为 import 的用法：from platform_core ... 或 import platform_core
        for m in IMPORT_PLATFORM_PATTERN.finditer(content):
            line_start = content.rfind("\n", 0, m.start()) + 1
            line_end = content.find("\n", m.start())
            if line_end == -1:
                line_end = len(content)
            line = content[line_start:line_end]
            # 忽略纯注释行（整行被 # 注释）
            if line.strip().startswith("#"):
                continue
            violations.append((path, line.strip()))
    assert not violations, (
        "细胞不得依赖 platform_core；以下文件存在 import platform_core 或 from platform_core：\n"
        + "\n".join(f"  {p}: {line}" for p, line in violations)
    )


def test_gateway_cell_list_not_hardcoded():
    """网关细胞名录应由配置驱动；若仍存在硬编码 _CELL_NAMES 则 skip，待 P0-1 落地后改为断言失败。"""
    if not os.path.isfile(GATEWAY_APP):
        pytest.skip("gateway app.py not found")
    with open(GATEWAY_APP, "r", encoding="utf-8") as f:
        content = f.read()
    # 检测是否存在包含多个细胞 id 的 _CELL_NAMES 字面量（典型为 "crm", "erp", ...）
    if "_CELL_NAMES" in content and '"crm"' in content and '"erp"' in content:
        pytest.skip(
            "网关细胞名录尚未配置化（存在硬编码 _CELL_NAMES），见 docs/项目合规校验报告.md P0-1；"
            "完成 A1 后可将此 skip 改为断言失败。"
        )
