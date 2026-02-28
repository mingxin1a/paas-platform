#!/usr/bin/env python3
"""
CRM 细胞交付校验脚本：符合 delivery.package.schema.md 与 completion.manifest。
校验项：delivery.package 存在、completion.manifest 存在、单元测试通过、健康接口可用。
用法：在 cells/crm 目录下执行 python scripts/verify_delivery.py 或 pytest tests/unit/test_fastapi_crm.py -v
"""
from __future__ import annotations

import os
import sys
import subprocess
from pathlib import Path

CELL_ROOT = Path(__file__).resolve().parent.parent
os.chdir(CELL_ROOT)
sys.path.insert(0, str(CELL_ROOT))


def main():
    errors = []
    # 1. delivery.package
    if not (CELL_ROOT / "delivery.package").is_file():
        errors.append("缺少 delivery.package")
    # 2. completion.manifest
    if not (CELL_ROOT / "completion.manifest").is_file():
        errors.append("缺少 completion.manifest")
    # 3. cell_profile / 细胞档案
    if not (CELL_ROOT / "cell_profile.md").is_file():
        errors.append("缺少 cell_profile.md")
    # 4. 单元测试（使用临时文件 SQLite，保证请求间数据共享）
    env = os.environ.copy()
    import tempfile
    _t = Path(tempfile.gettempdir()) / "crm_verify_test.db"
    env["CRM_DATABASE_URL"] = f"sqlite:///{_t.as_posix()}"
    r = subprocess.run(
        [sys.executable, "-m", "pytest", "tests/unit/test_fastapi_crm.py", "-v", "--tb=short", "-q"],
        cwd=CELL_ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
    )
    if r.returncode != 0:
        errors.append("单元测试未通过: " + (r.stderr or r.stdout or "")[:500])
    # 5. 健康接口（可选：若服务未启动则跳过）
    try:
        from fastapi.testclient import TestClient
        from src.main import app
        client = TestClient(app)
        resp = client.get("/health")
        if resp.status_code != 200 or resp.json().get("status") != "up":
            errors.append("健康接口返回异常")
    except Exception as e:
        errors.append(f"健康接口校验异常: {e}")

    if errors:
        print("交付校验失败:")
        for e in errors:
            print("  -", e)
        sys.exit(1)
    print("交付校验通过：delivery.package、completion.manifest、cell_profile、单元测试、健康接口均符合规范。")
    sys.exit(0)


if __name__ == "__main__":
    main()
