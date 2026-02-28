#!/usr/bin/env python3
"""
全项目标准化商用交付包构建脚本。
执行后于 dist/ 下生成：01_平台核心包、02_分模块交付包、03_文档包、04_测试包、05_部署工具包，
并生成《商用交付包使用说明》及整体压缩包。
用法: python scripts/build_full_delivery.py
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
SKIP_SUFFIX = (".pyc", ".pyo", ".tsbuildinfo")
SKIP_FILES = {".DS_Store", "Thumbs.db"}

# 业务细胞列表（排除模板）
CELL_IDS = ["crm", "erp", "oa", "srm", "mes", "wms", "tms", "hrm", "plm", "ems", "his", "lis", "lims"]

# 文档分类（路径相对 docs/）：总交付手册、架构、部署运维、用户操作、管理员、合规、验收
DOC_CATEGORIES = {
    "总交付手册": ["商用化交付总手册.md", "商用交付包目录结构.md", "commercial_delivery/超级PaaS平台商用交付总手册.md", "commercial_delivery/README.md"],
    "架构文档": ["项目目录与架构说明.md", "02_概要设计说明书.md", "超级PaaS平台全量化系统架构设计说明书.md", "架构对齐与开发指南.md", "架构不合规问题清单.md", "全项目架构合规性校验报告.md"],
    "部署运维手册": ["生产级部署运维手册.md", "PaaS核心运维手册.md", "commercial_delivery/PaaS层/PaaS核心层商用运维手册.md", "commercial_delivery/PaaS层/PaaS核心层高可用配置指南.md", "监控告警体系使用手册.md", "CI-CD自动化流水线使用手册.md", "数据备份与灾备手册.md"],
    "用户操作手册": ["前端控制台使用说明.md", "commercial_delivery/细胞/CRM/CRM用户操作手册.md", "commercial_delivery/细胞/ERP/ERP用户操作手册.md", "commercial_delivery/细胞/WMS/WMS用户操作手册.md", "frontend/全模块前端功能适配说明.md", "frontend/企业级体验优化说明.md", "frontend/数据可视化与报表体系说明.md"],
    "管理员手册": ["commercial_delivery/细胞/CRM/CRM管理员手册.md", "commercial_delivery/细胞/ERP/ERP管理员手册.md", "commercial_delivery/细胞/WMS/WMS管理员手册.md", "多租户能力使用手册.md", "commercial_delivery/通用/超级PaaS平台多租户配置指南.md"],
    "合规文档": ["全平台安全合规加固说明.md", "commercial_delivery/通用/超级PaaS平台安全合规手册.md", "GDPR与三权分立设计.md", "敏感数据加密与脱敏规范.md", "security/安全合规说明.md", "security/安全渗透测试报告.md"],
    "验收清单": ["commercial_delivery/通用/超级PaaS平台商用验收清单.md", "零心智负担与3-Click验收清单.md", "commercial_delivery/批次1_商用验收测试用例.md", "全项目测试体系说明.md", "测试验证体系说明.md"],
}


def _should_skip(path: Path, base: Path) -> bool:
    rel = path.relative_to(base) if base in path.parents else path
    parts = rel.parts
    if any(p in SKIP_DIRS for p in parts):
        return True
    if path.is_file():
        if path.suffix in SKIP_SUFFIX or path.name in SKIP_FILES:
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
            if f.endswith(SKIP_SUFFIX) or f in SKIP_FILES or f.startswith("."):
                continue
            src_f = root / f
            dst_f = dst / rel / f
            shutil.copy2(src_f, dst_f)


def build_platform_core(delivery_root: Path) -> None:
    """01_平台核心包：PaaS 核心代码、Docker、部署配置、运维工具。"""
    out = delivery_root / "01_平台核心包"
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
    # 说明
    (out / "README.txt").write_text("平台核心包：含 PaaS 核心代码、部署脚本、运维工具。部署见《商用交付包使用说明》。", encoding="utf-8")


def build_cell_package(cell_id: str, delivery_root: Path) -> None:
    """单个细胞交付包：代码、镜像相关、部署配置、接口文档、用户手册。"""
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
    (out / "README.txt").write_text(f"细胞 {cell_id} 交付包：代码、部署配置、接口文档、用户手册。", encoding="utf-8")


def build_docs_package(delivery_root: Path) -> None:
    """03_文档包：按分类整理商用交付文档。"""
    out = delivery_root / "03_文档包"
    docs_root = ROOT / "docs"
    for cat, names in DOC_CATEGORIES.items():
        cat_dir = out / cat
        cat_dir.mkdir(parents=True, exist_ok=True)
        for name in names:
            src = docs_root / name
            if src.is_file():
                shutil.copy2(src, cat_dir / src.name)
    for sub in ["commercial_delivery", "performance", "security", "frontend", "细胞档案", "api"]:
        sp = docs_root / sub
        if sp.is_dir() and sub not in DOC_CATEGORIES:
            copy_tree(sp, out / sub)
    (out / "README.txt").write_text("文档包：总交付手册、架构、部署运维、用户/管理员手册、合规、验收清单。", encoding="utf-8")


def build_test_package(delivery_root: Path) -> None:
    """04_测试包：测试用例、脚本、报告、验收工具。"""
    out = delivery_root / "04_测试包"
    out.mkdir(parents=True, exist_ok=True)
    tests_root = ROOT / "tests"
    if tests_root.is_dir():
        (out / "测试用例").mkdir(exist_ok=True)
        copy_tree(tests_root, out / "测试用例")
    for name in ["deploy/core_business_flow_tests.py", "deploy/smoke_test.py"]:
        p = ROOT / name
        if p.is_file():
            (out / "测试脚本").mkdir(exist_ok=True)
            shutil.copy2(p, out / "测试脚本" / Path(name).name)
    reports = ROOT / "docs" / "performance"
    if reports.is_dir():
        (out / "测试报告").mkdir(exist_ok=True)
        for f in reports.glob("*.md"):
            shutil.copy2(f, out / "测试报告" / f.name)
    (out / "验收工具").mkdir(exist_ok=True)
    for s in ["scripts/self_check.py", "evolution_engine/verify_all_cells.py", "evolution_engine/verify_delivery.py"]:
        p = ROOT / s
        if p.is_file():
            shutil.copy2(p, out / "验收工具" / p.name)
    (out / "README.txt").write_text("测试包：全量测试用例、测试脚本、测试报告、验收工具。", encoding="utf-8")


def build_deploy_tools(delivery_root: Path) -> None:
    """05_部署工具包：部署脚本、编排、配置。"""
    out = delivery_root / "05_部署工具包"
    out.mkdir(parents=True, exist_ok=True)
    deploy = ROOT / "deploy"
    if deploy.is_dir():
        copy_tree(deploy, out)
    for name in ["run.sh", ".editorconfig"]:
        p = ROOT / name
        if p.is_file():
            shutil.copy2(p, out / name)
    (out / "README.txt").write_text("部署工具包：网关/细胞启动脚本、docker-compose、k8s、环境配置示例。", encoding="utf-8")


def create_usage_doc(delivery_root: Path, stamp: str) -> None:
    """生成《商用交付包使用说明》到交付根目录（含版本戳）。"""
    content = _usage_content(stamp)
    target = delivery_root / "商用交付包使用说明.md"
    target.write_text(content, encoding="utf-8")


def _usage_content(stamp: str) -> str:
    return f"""# 商用交付包使用说明

**交付包版本**：{stamp}  
**生成时间**：{datetime.now().strftime("%Y-%m-%d %H:%M")}

---

## 一、交付包内容

| 目录 | 说明 |
|------|------|
| **01_平台核心包** | PaaS 核心层代码、Docker 相关、部署配置、运维工具 |
| **02_分模块交付包** | 各业务 Cell 独立包（代码、镜像、部署配置、接口文档、用户手册） |
| **03_文档包** | 总交付手册、架构文档、部署运维手册、用户/管理员手册、合规文档、验收清单 |
| **04_测试包** | 全量测试用例、测试脚本、测试报告、验收测试工具 |
| **05_部署工具包** | 一键部署脚本、docker-compose、k8s 配置、环境示例 |

---

## 二、部署步骤

1. **环境准备**：Python 3.8+、Node 18+（前端）、Docker（可选）。
2. **平台核心**：从 `01_平台核心包/deploy` 执行 `python run_gateway.py`，网关默认端口 8000。
3. **细胞部署**：各细胞从 `02_分模块交付包/cell_<id>` 按 README 或 Dockerfile 部署，并配置网关路由（环境变量或 `GATEWAY_ROUTES_PATH`）。
4. **前端**：从项目根目录或交付包外获取 frontend/frontend-admin，执行 `npm install && npm run build`，或通过网关静态目录托管。
5. **验收**：使用 `04_测试包/验收工具` 及 `03_文档包/验收清单` 执行验收。

详细步骤见 `03_文档包/部署运维手册` 及 `03_文档包/总交付手册`。

---

## 三、验收标准

- 网关 `/health` 返回 200；各细胞经网关 `/api/v1/<cell>/health` 可达。
- 登录、列表、创建等核心流程按《商用验收清单》通过。
- 安全、性能、合规按《安全合规说明》《性能测试报告》及验收清单执行。

---

## 四、售后支持说明

- 文档与问题清单：见 `03_文档包` 与项目 `docs/`。
- 缺陷与需求：通过项目 Issue 或商务约定渠道反馈。
- 版本与补丁：以交付包版本号及发布说明为准。
"""


def main() -> int:
    stamp = datetime.now().strftime("%Y%m%d")
    delivery_name = f"SuperPaaS_Delivery_{stamp}"
    delivery_root = DIST / delivery_name

    if delivery_root.exists():
        shutil.rmtree(delivery_root)
    delivery_root.mkdir(parents=True, exist_ok=True)

    print("[build_full_delivery] 生成 01_平台核心包 ...")
    build_platform_core(delivery_root)

    print("[build_full_delivery] 生成 02_分模块交付包 ...")
    (delivery_root / "02_分模块交付包").mkdir(exist_ok=True)
    for cid in CELL_IDS:
        build_cell_package(cid, delivery_root)

    print("[build_full_delivery] 生成 03_文档包 ...")
    build_docs_package(delivery_root)

    print("[build_full_delivery] 生成 04_测试包 ...")
    build_test_package(delivery_root)

    print("[build_full_delivery] 生成 05_部署工具包 ...")
    build_deploy_tools(delivery_root)

    print("[build_full_delivery] 生成《商用交付包使用说明》...")
    create_usage_doc(delivery_root, stamp)

    zip_name = DIST / f"{delivery_name}.zip"
    print(f"[build_full_delivery] 打包 {zip_name} ...")
    with zipfile.ZipFile(zip_name, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(delivery_root):
            dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
            for f in files:
                path = Path(root) / f
                arc = path.relative_to(delivery_root.parent).as_posix()
                zf.write(path, arc)

    print(f"[build_full_delivery] 已生成: {delivery_root}")
    print(f"[build_full_delivery] 压缩包: {zip_name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
