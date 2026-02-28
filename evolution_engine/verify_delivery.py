#!/usr/bin/env python3
"""
细胞交付验证（跨平台）
用法: python evolution_engine/verify_delivery.py {CELL_NAME}
退出码: 0 通过, 非0 未通过
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def main():
    if len(sys.argv) != 2:
        print("usage: python evolution_engine/verify_delivery.py CELL_NAME", file=sys.stderr)
        sys.exit(2)
    cell_name = sys.argv[1].strip().lower()
    cell_dir = os.path.join(ROOT, "cells", cell_name)
    if not os.path.isdir(cell_dir):
        print(f"ERROR: cell directory not found: {cell_dir}", file=sys.stderr)
        sys.exit(1)
    print(f"[verify] cell={cell_name}")

    # 1. delivery.package
    pkg = os.path.join(cell_dir, "delivery.package")
    if not os.path.isfile(pkg):
        print("FAIL: missing delivery.package", file=sys.stderr)
        sys.exit(1)
    print("[verify] delivery.package OK")

    # 2. completion.manifest (from delivery.package or default)
    manifest_name = "completion.manifest"
    with open(pkg, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip().startswith("completion_manifest:"):
                manifest_name = line.split(":", 1)[1].strip().strip("'\"").strip()
                break
    manifest_path = os.path.join(cell_dir, manifest_name)
    if not os.path.isfile(manifest_path):
        print(f"FAIL: missing {manifest_name}", file=sys.stderr)
        sys.exit(1)
    print("[verify] completion.manifest OK")

    # 3. cell_profile.md + api_contract.yaml
    for f in ("cell_profile.md", "api_contract.yaml"):
        if not os.path.isfile(os.path.join(cell_dir, f)):
            print(f"FAIL: missing {f}", file=sys.stderr)
            sys.exit(1)
    print("[verify] cell_profile.md + api_contract.yaml OK")

    # 4. auto_healing.yaml
    if not os.path.isfile(os.path.join(cell_dir, "auto_healing.yaml")):
        print("FAIL: missing auto_healing.yaml", file=sys.stderr)
        sys.exit(1)
    print("[verify] auto_healing.yaml OK")

    # 5. 可运行性：src/app.py 必须存在
    app_py = os.path.join(cell_dir, "src", "app.py")
    if not os.path.isfile(app_py):
        print("FAIL: missing src/app.py (cell not runnable)", file=sys.stderr)
        sys.exit(1)
    print("[verify] src/app.py OK")

    # 6. 独立交付物（建议）
    for f in ("Dockerfile", "README.md", "dist/PACKAGE.md"):
        p = os.path.join(cell_dir, f)
        if not os.path.isfile(p):
            print(f"[verify] WARN: missing {f}", file=sys.stderr)
    print("[verify] optional Dockerfile/README/dist checked")

    print(f"[verify] all checks passed for {cell_name}")
    sys.exit(0)


if __name__ == "__main__":
    main()
