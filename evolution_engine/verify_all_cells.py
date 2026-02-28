#!/usr/bin/env python3
"""
全细胞交付校验：对项目中所有细胞执行 verify_delivery，汇总通过/失败。
用法: python evolution_engine/verify_all_cells.py [--list]
退出码: 0 全部通过, 非0 存在未通过
"""
import os
import sys
import subprocess

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CELLS_DIR = os.path.join(ROOT, "cells")
VERIFY_SCRIPT = os.path.join(ROOT, "evolution_engine", "verify_delivery.py")

# 所有应参与校验的细胞（按 cells 目录下存在且为目录的为准，再按此顺序）
DEFAULT_CELLS = [
    "crm", "erp", "wms", "hrm", "oa", "mes",
    "tms", "srm", "plm", "ems", "his", "lis", "lims",
]


def discover_cells():
    """发现 cells 目录下所有子目录（细胞名）。"""
    if not os.path.isdir(CELLS_DIR):
        return []
    out = []
    for name in sorted(os.listdir(CELLS_DIR)):
        path = os.path.join(CELLS_DIR, name)
        if os.path.isdir(path) and not name.startswith("."):
            out.append(name)
    return out


def main():
    if "--list" in sys.argv:
        cells = discover_cells()
        for c in cells:
            print(c)
        return 0

    cells = discover_cells()
    if not cells:
        print("[verify_all] no cells found under cells/", file=sys.stderr)
        sys.exit(1)

    print(f"[verify_all] checking {len(cells)} cells: {', '.join(cells)}")
    failed = []
    for cell in cells:
        ret = subprocess.run(
            [sys.executable, VERIFY_SCRIPT, cell],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=30,
        )
        if ret.returncode != 0:
            failed.append(cell)
            print(f"[verify_all] FAIL: {cell}")
            if ret.stderr:
                print(ret.stderr.strip(), file=sys.stderr)
        else:
            print(f"[verify_all] OK: {cell}")

    if failed:
        print(f"[verify_all] {len(failed)} cell(s) failed: {', '.join(failed)}", file=sys.stderr)
        sys.exit(1)
    print(f"[verify_all] all {len(cells)} cells passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
