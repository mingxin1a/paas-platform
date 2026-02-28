#!/usr/bin/env python3
"""
行业解决方案交付包构建脚本。
按解决方案类型只打包平台核心 + 该方案所需 Cell + 解决方案文档，生成标准化交付包。
用法:
  python scripts/build_solution_delivery.py --solution manufacturing
  python scripts/build_solution_delivery.py --solution trade
  python scripts/build_solution_delivery.py --solution healthcare
"""
from __future__ import annotations

import os
import shutil
import zipfile
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DIST = ROOT / "dist"
SKIP_DIRS = {".git", "__pycache__", "node_modules", ".pytest_cache", ".cursor", ".venv", "venv", "dist", ".idea", ".vscode"}

SOLUTIONS = {
    "manufacturing": {
        "name": "通用制造业",
        "cells": ["erp", "mes", "wms", "srm", "tms"],
        "doc_dir": "manufacturing",
    },
    "trade": {
        "name": "通用贸易企业",
        "cells": ["crm", "erp", "wms", "srm", "oa"],
        "doc_dir": "trade",
    },
    "healthcare": {
        "name": "医疗行业",
        "cells": ["his", "lis", "oa", "erp"],
        "doc_dir": "healthcare",
    },
}


def _should_skip(path: Path, base: Path) -> bool:
    rel = path.relative_to(base) if base in path.parents else path
    parts = rel.parts
    if any(p in SKIP_DIRS for p in parts):
        return True
    if path.is_file():
        if path.suffix in (".pyc", ".pyo", ".tsbuildinfo") or path.name in {".DS_Store", "Thumbs.db"}:
            return True
        if path.name.startswith("."):
            return True
    return False


def copy_tree(src: Path, dst: Path, exclude_dirs: set | None = None) -> None:
    exclude = (exclude_dirs or set()) | SKIP_DIRS
    for root, dirs, files in os.walk(src):
        root = Path(root)
        dirs[:] = [d for d in dirs if d not in exclude and not d.startswith(".")]
        rel = root.relative_to(src)
        (dst / rel).mkdir(parents=True, exist_ok=True)
        for f in files:
            if f.endswith((".pyc", ".pyo")) or f in {".DS_Store", "Thumbs.db"} or f.startswith("."):
                continue
            src_f = root / f
            dst_f = dst / rel / f
            shutil.copy2(src_f, dst_f)


def build_platform_core(out: Path) -> None:
    """01_平台核心包：PaaS 核心、部署脚本、运维工具。"""
    out.mkdir(parents=True, exist_ok=True)
    pc = ROOT / "platform_core"
    if pc.is_dir():
        (out / "code").mkdir(exist_ok=True)
        copy_tree(pc, out / "code")
    deploy = ROOT / "deploy"
    if deploy.is_dir():
        (out / "deploy").mkdir(exist_ok=True)
        for name in ["run_gateway.py", "run_datalake.py", "run_sync_worker.py", "run_governance.py", "smoke_test.py", ".env.example"]:
            p = deploy / name
            if p.exists():
                shutil.copy2(p, out / "deploy" / name)
        for sub in ["config", "k8s", "load_test"]:
            sp = deploy / sub
            if sp.is_dir():
                copy_tree(sp, out / "deploy" / sub)
    scripts = ROOT / "scripts"
    if scripts.is_dir():
        (out / "运维工具").mkdir(exist_ok=True)
        for f in scripts.glob("*.py"):
            if "build_full_delivery" not in f.name and "build_batch1" not in f.name:
                shutil.copy2(f, out / "运维工具" / f.name)
        for f in scripts.glob("*.sh"):
            shutil.copy2(f, out / "运维工具" / f.name)
    (out / "README.txt").write_text("平台核心包：PaaS 核心代码、部署脚本、运维工具。", encoding="utf-8")


def build_cell_package(cell_id: str, delivery_root: Path) -> None:
    """单个细胞交付包。"""
    out = delivery_root / "02_分模块交付包" / f"cell_{cell_id}"
    out.mkdir(parents=True, exist_ok=True)
    cell_path = ROOT / "cells" / cell_id
    if not cell_path.is_dir():
        return
    (out / "code").mkdir(exist_ok=True)
    copy_tree(cell_path, out / "code")
    for name in ["Dockerfile", "docker-compose.yml", "requirements.txt", "api_contract.yaml", "README.md", "delivery.package", "cell_profile.md"]:
        p = cell_path / name
        if p.is_file():
            shutil.copy2(p, out / name)
    (out / "部署配置").mkdir(exist_ok=True)
    for sub in ["docker", "k8s"]:
        sp = cell_path / sub
        if sp.is_dir():
            copy_tree(sp, out / "部署配置" / sub)
    (out / "接口文档").mkdir(exist_ok=True)
    doc_cell = ROOT / "docs" / "commercial_delivery" / "细胞"
    for upper in [cell_id.upper(), cell_id.capitalize()]:
        doc_dir = doc_cell / upper
        if doc_dir.is_dir():
            for f in doc_dir.glob("*.md"):
                if "接口" in f.name or "api" in f.name.lower():
                    shutil.copy2(f, out / "接口文档" / f.name)
                    break
    cell_profile = ROOT / "docs" / "细胞档案" / f"{cell_id.upper()}_细胞档案.md"
    if cell_profile.is_file():
        shutil.copy2(cell_profile, out / "接口文档" / "细胞档案.md")
    (out / "用户手册").mkdir(exist_ok=True)
    for upper in [cell_id.upper(), cell_id.capitalize()]:
        doc_dir = doc_cell / upper
        if doc_dir.is_dir():
            for f in doc_dir.glob("*用户*.md"):
                shutil.copy2(f, out / "用户手册" / f.name)
            for f in doc_dir.glob("*管理员*.md"):
                shutil.copy2(f, out / "用户手册" / f.name)
    (out / "README.txt").write_text(f"细胞 {cell_id} 交付包。", encoding="utf-8")


def build_solution_docs(delivery_root: Path, doc_dir: str) -> None:
    """03_解决方案文档包：行业方案专属文档。"""
    out = delivery_root / "03_解决方案文档包"
    out.mkdir(parents=True, exist_ok=True)
    src = ROOT / "docs" / "solutions" / doc_dir
    if not src.is_dir():
        return
    for f in src.glob("*.md"):
        shutil.copy2(f, out / f.name)
    (out / "README.txt").write_text("本目录为行业解决方案专属文档：痛点分析、方案架构、功能清单、部署方案、实施计划、实施手册、验收清单、成功案例模板、报价模板；医疗方案含合规适配说明。", encoding="utf-8")


def build_deploy_tools(delivery_root: Path) -> None:
    """04_部署工具包。"""
    out = delivery_root / "04_部署工具包"
    out.mkdir(parents=True, exist_ok=True)
    deploy = ROOT / "deploy"
    if deploy.is_dir():
        copy_tree(deploy, out)
    for name in ["run.sh", ".editorconfig"]:
        p = ROOT / name
        if p.is_file():
            shutil.copy2(p, out / name)
    (out / "README.txt").write_text("部署工具包：网关/细胞启动脚本、docker-compose、k8s、环境配置示例。", encoding="utf-8")


def create_solution_readme(delivery_root: Path, solution_id: str, name: str, cells: list[str]) -> None:
    """生成解决方案交付包使用说明。"""
    cells_str = "、".join(cells)
    content = f"""# {name}解决方案 · 交付包使用说明

**生成时间**：{datetime.now().strftime("%Y-%m-%d %H:%M")}

---

## 一、交付包内容

| 目录 | 说明 |
|------|------|
| **01_平台核心包** | PaaS 核心层代码、部署脚本、运维工具 |
| **02_分模块交付包** | 本方案所含 Cell：{cells_str} |
| **03_解决方案文档包** | 行业痛点分析、方案架构、功能清单、部署方案、实施计划、实施手册、验收清单、成功案例模板、报价模板 |
| **04_部署工具包** | 网关/细胞启动脚本、docker-compose、k8s、环境配置示例 |

---

## 二、部署顺序

1. 部署网关，配置路由（仅指向本方案所含 Cell 的 URL）。
2. 按需部署各 Cell（{cells_str}）。
3. 部署前端，配置网关地址。
4. 执行验收：`python scripts/run_acceptance_test.py`（需网关仅路由本方案 Cell）或分模块 `run_module_acceptance.py <cell_id>`。

---

## 三、验收依据

- 本方案验收清单见 **03_解决方案文档包** 中《验收清单》。
- 自动化验收脚本与全平台验收总清单一致，仅执行本方案涉及 Cell 的项。

---

## 四、架构原则

- 严格遵循细胞化架构，模块按需选配、灵活增减，不修改平台核心。
- 扩展其他 Cell 时，仅新增 Cell 与网关路由配置即可。

---

**文档归属**：行业解决方案包 · {name}
"""
    (delivery_root / "解决方案交付包使用说明.md").write_text(content, encoding="utf-8")


def main() -> int:
    import sys
    solution_id = None
    for i, a in enumerate(sys.argv):
        if a == "--solution" and i + 1 < len(sys.argv):
            solution_id = sys.argv[i + 1].strip().lower()
            break
    if solution_id not in SOLUTIONS:
        print("用法: python scripts/build_solution_delivery.py --solution <manufacturing|trade|healthcare>")
        print("  manufacturing: 通用制造业（ERP+MES+WMS+SRM+TMS）")
        print("  trade:         通用贸易企业（CRM+ERP+WMS+SRM+OA）")
        print("  healthcare:   医疗行业（HIS+LIS+OA+ERP）")
        return 1
    info = SOLUTIONS[solution_id]
    stamp = datetime.now().strftime("%Y%m%d")
    delivery_name = f"Solution_{solution_id.capitalize()}_{stamp}"
    delivery_root = DIST / delivery_name
    if delivery_root.exists():
        shutil.rmtree(delivery_root)
    delivery_root.mkdir(parents=True, exist_ok=True)
    print(f"[build_solution_delivery] 生成 {info['name']} 解决方案交付包 ...")
    print("[build_solution_delivery] 01_平台核心包 ...")
    build_platform_core(delivery_root / "01_平台核心包")
    print("[build_solution_delivery] 02_分模块交付包 ...")
    (delivery_root / "02_分模块交付包").mkdir(exist_ok=True)
    for cid in info["cells"]:
        build_cell_package(cid, delivery_root)
    print("[build_solution_delivery] 03_解决方案文档包 ...")
    build_solution_docs(delivery_root, info["doc_dir"])
    print("[build_solution_delivery] 04_部署工具包 ...")
    build_deploy_tools(delivery_root)
    print("[build_solution_delivery] 解决方案交付包使用说明 ...")
    create_solution_readme(delivery_root, solution_id, info["name"], info["cells"])
    zip_name = DIST / f"{delivery_name}.zip"
    print(f"[build_solution_delivery] 打包 {zip_name} ...")
    with zipfile.ZipFile(zip_name, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(delivery_root):
            dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
            for f in files:
                path = Path(root) / f
                arc = path.relative_to(delivery_root.parent).as_posix()
                zf.write(path, arc)
    print(f"[build_solution_delivery] 已生成: {delivery_root}")
    print(f"[build_solution_delivery] 压缩包: {zip_name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
