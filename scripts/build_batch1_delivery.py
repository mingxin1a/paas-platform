#!/usr/bin/env python3
"""
批次1 标准化商用交付包生成脚本。
产出：dist/batch1_commercial_YYYYMMDD.zip，含 CRM/ERP/OA/SRM 细胞、平台核心、双端前端构建、商用文档。
细胞独立库/独立部署、仅 HTTP 调用 PaaS 核心；不引入跨细胞耦合。
"""
from __future__ import annotations

import os
import zipfile
import shutil
from datetime import datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIST = os.path.join(ROOT, "dist")
BATCH1_CELLS = ["crm", "erp", "oa", "srm"]


def _add_dir(zf: zipfile.ZipFile, base: str, arc_prefix: str, exclude_dirs=None) -> None:
    exclude_dirs = exclude_dirs or set()
    for root, dirs, files in os.walk(base):
        dirs[:] = [d for d in dirs if d not in {".git", "__pycache__", "node_modules", ".pytest_cache", ".cursor"}]
        for d in exclude_dirs:
            if d in dirs:
                dirs.remove(d)
        for f in files:
            if f.endswith(".pyc") or f.startswith("."):
                continue
            path = os.path.join(root, f)
            arc = os.path.join(arc_prefix, os.path.relpath(path, base))
            zf.write(path, arc)


def main() -> int:
    os.makedirs(DIST, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d")
    out_name = os.path.join(DIST, f"batch1_commercial_{stamp}.zip")

    with zipfile.ZipFile(out_name, "w", zipfile.ZIP_DEFLated) as zf:
        # 平台核心（网关、审计、签名、敏感数据处理）
        pc = os.path.join(ROOT, "platform_core")
        if os.path.isdir(pc):
            _add_dir(zf, pc, "platform_core")

        # 批次1 细胞
        for cell in BATCH1_CELLS:
            cell_path = os.path.join(ROOT, "cells", cell)
            if os.path.isdir(cell_path):
                _add_dir(zf, cell_path, f"cells/{cell}")

        # 部署与脚本
        for name in ["deploy", "scripts"]:
            path = os.path.join(ROOT, name)
            if os.path.isdir(path):
                _add_dir(zf, path, name)

        # 商用文档
        doc = os.path.join(ROOT, "docs", "commercial_delivery")
        if os.path.isdir(doc):
            _add_dir(zf, doc, "docs/commercial_delivery")
        for name in ["README.md", "run.sh"]:
            p = os.path.join(ROOT, name)
            if os.path.isfile(p):
                zf.write(p, name)

        # 前端（若已构建则打包 dist，否则仅 package.json 等说明）
        for fe in ["frontend", "frontend-admin"]:
            fe_path = os.path.join(ROOT, fe)
            if os.path.isdir(fe_path):
                _add_dir(zf, fe_path, fe, exclude_dirs={"node_modules"})

    print(f"[build_batch1_delivery] 已生成: {out_name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
