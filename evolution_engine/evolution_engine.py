#!/usr/bin/env python3
"""
SuperPaaS 自主进化引擎 - 单次周期
感知 → 对标 → 进化 → 验证 → 透明化。可被 cron / 计划任务每 24 小时调用。
约束：永不联网、永不越界、自我终止（维护模式）。
"""
from __future__ import annotations

import os
import re
import sys
import json
import subprocess
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Tuple

ROOT = Path(__file__).resolve().parent.parent
CELLS_DIR = ROOT / "cells"
GLASS_HOUSE = ROOT / "glass_house"
GAP_DIR = GLASS_HOUSE / "gap_analysis"
STATE_DIR = GLASS_HOUSE / "state"
LOG_FILE = GLASS_HOUSE / "live_evolution_log.md"
CONSTITUTION_00 = ROOT / "docs" / "00_【最高宪法】SuperPaaS-God.md"
CONSTITUTION_01 = ROOT / "docs" / "01_【​核心法律】基础与AI安全宪法.md"


def _parse_yaml_like(path: Path) -> dict:
    data = {}
    if not path.exists():
        return data
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            m = re.match(r"^(\w+):\s*(.*)$", line.strip())
            if m:
                key, val = m.group(1), m.group(2).strip().strip("'\"").strip()
                data[key] = val
    return data


def _write_yaml_like(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for k, v in data.items():
            f.write(f"{k}: {v}\n")
    return None


# ---------- 感知 (Sense) ----------
def sense() -> List[Tuple[str, Path, dict]]:
    """扫描所有细胞的 delivery.package，返回 (cell_name, cell_dir, pkg) 且 status 为 building 或 ready_for_qa。"""
    pending = []
    if not CELLS_DIR.exists():
        return pending
    for d in CELLS_DIR.iterdir():
        if not d.is_dir():
            continue
        pkg_path = d / "delivery.package"
        if not pkg_path.exists():
            continue
        pkg = _parse_yaml_like(pkg_path)
        status = (pkg.get("status") or "").strip().lower()
        if status in ("building", "ready_for_qa"):
            pending.append((d.name, d, pkg))
    return pending


# ---------- 对标 (Benchmark) ----------
def benchmark(cell_name: str, cell_dir: Path) -> Path:
    """生成《{CELL_NAME}_gap_analysis.md》到 glass_house/gap_analysis/，返回路径。"""
    GAP_DIR.mkdir(parents=True, exist_ok=True)
    out = GAP_DIR / f"{cell_name}_gap_analysis.md"
    profile = cell_dir / "cell_profile.md"
    contract = cell_dir / "api_contract.yaml"
    profile_preview = ""
    if profile.exists():
        with open(profile, "r", encoding="utf-8") as f:
            profile_preview = f.read(2000)
    contract_preview = ""
    if contract.exists():
        with open(contract, "r", encoding="utf-8") as f:
            contract_preview = f.read(1500)
    content = f"""# {cell_name.upper()} 细胞 - 业界对标与差距分析

**生成时间**：{datetime.now().isoformat()}  
**约束文档**：《00_最高宪法》SuperPaaS-God v8.0、《01_核心法律》基础与AI安全宪法 V3.0

---

## 1. 细胞档案摘要

<details>
<summary>cell_profile 摘要</summary>

```
{profile_preview[:1500]}
```
</details>

---

## 2. API 契约摘要

<details>
<summary>api_contract 摘要</summary>

```
{contract_preview[:1200]}
```
</details>

---

## 3. 对标维度（内置知识，未联网）

| 维度 | 业界常规 | 当前细胞 | 差距 | 可实现性 |
|------|----------|----------|------|----------|
| 接口契约 | OpenAPI 3 + 必须头/幂等 | 见 api_contract | 按契约补齐实现 | 高 |
| 细胞自治 | 独立库/独立部署/独立失效 | 见 cell_profile | 确保无跨细胞直连 | 高 |
| 管家式 AI | 意图预判、自愈规则 | auto_healing.yaml + ai_agent | 与监控中心联动 | 高 |
| 可观测性 | trace_id、JSON 日志 | 需在实现中保证 | 接入平台全链路 | 高 |

---

## 4. 合规性初筛

- 仅当功能符合《00_最高宪法》与《01_核心法律》时启动开发任务。
- 跨细胞禁止同步强一致、禁止直连库；敏感数据动态脱敏；事件语义冻结。

---

## 5. 建议进化任务（供下一周期或人工执行）

1. 确保 delivery.package 中 completion.manifest 与实现一致。
2. 运行 `./verify_delivery.sh {cell_name}` 或 `python evolution_engine/verify_delivery.py {cell_name}` 通过后置为 production_ready。
3. 向 PaaS 注册中心宣告（写入 glass_house/state/registry.json 或平台约定接口）。

"""
    with open(out, "w", encoding="utf-8") as f:
        f.write(content)
    return out


# ---------- 验证 (Validate) ----------
def run_verify(cell_name: str) -> bool:
    """执行 verify_delivery，返回是否通过。"""
    script = ROOT / "evolution_engine" / "verify_delivery.py"
    if not script.exists():
        script = ROOT / "verify_delivery.sh"
        cmd = ["sh", str(script), cell_name]
    else:
        cmd = [sys.executable, str(script), cell_name]
    try:
        r = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, timeout=30)
        return r.returncode == 0
    except Exception:
        return False


def set_production_ready(cell_name: str) -> None:
    """将 cells/{cell_name}/delivery.package 的 status 置为 production_ready，更新 last_evolution_at。"""
    pkg_path = CELLS_DIR / cell_name / "delivery.package"
    if not pkg_path.exists():
        return
    pkg = _parse_yaml_like(pkg_path)
    pkg["status"] = "production_ready"
    pkg["last_evolution_at"] = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    _write_yaml_like(pkg_path, pkg)


def announce_to_registry(cell_name: str) -> None:
    """向 PaaS 注册中心宣告（写入 glass_house/state/registry.json）。"""
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    registry_path = STATE_DIR / "registry.json"
    registry = []
    if registry_path.exists():
        try:
            with open(registry_path, "r", encoding="utf-8") as f:
                registry = json.load(f)
        except Exception:
            registry = []
    entry = {"cell": cell_name, "status": "production_ready", "at": datetime.now().isoformat()}
    if not any(r.get("cell") == cell_name for r in registry):
        registry.append(entry)
    else:
        registry = [r for r in registry if r.get("cell") != cell_name] + [entry]
    with open(registry_path, "w", encoding="utf-8") as f:
        json.dump(registry, f, ensure_ascii=False, indent=2)


# ---------- 透明化 (Glass House) ----------
def update_live_log(cycle_entries: List[str], cell_snapshot: List[Tuple[str, str, str, str]], maintenance: bool) -> None:
    """更新 glass_house/live_evolution_log.md。"""
    GLASS_HOUSE.mkdir(parents=True, exist_ok=True)
    now = datetime.now().isoformat()
    snapshot_lines = ["| 细胞 | status | version | last_gap_at |", "|------|--------|---------|-------------|"]
    for row in cell_snapshot:
        name, status, version = row[0], row[1], row[2]
        last_gap = row[3] if len(row) > 3 else ""
        snapshot_lines.append(f"| {name} | {status} | {version} | {last_gap or '-'} |")
    log_body = "\n".join(cycle_entries) if cycle_entries else "*（本周期无待处理细胞或已进入维护模式）*"
    maintenance_val = "**是**（仅响应异常）" if maintenance else "否"
    content = f"""# SuperPaaS 自主进化引擎 - 实时演化日志

**玻璃房原则**：所有分析报告、状态变更、进化动作在此透明可见。

---

## 当前状态

| 项目 | 值 |
|------|-----|
| 引擎状态 | **单次周期已执行** |
| 维护模式 | {maintenance_val} |
| 上次周期 | {now} |

---

## 细胞交付状态快照

{chr(10).join(snapshot_lines)}

---

## 周期日志（最近优先）

{log_body}

---

## 约束声明

- **永不联网**：所有知识来自内置模型与本地文档。
- **永不越界**：仅执行符合《00_最高宪法》与《01_核心法律》的进化。
- **自我终止**：当所有细胞 production_ready 且连续 7 天无新 gap 时，进入维护模式。
"""
    with open(LOG_FILE, "w", encoding="utf-8") as f:
        f.write(content)


def collect_snapshot() -> List[Tuple[str, str, str, str]]:
    """收集所有细胞的 (name, status, version, last_gap_at)。"""
    snap = []
    if not CELLS_DIR.exists():
        return snap
    for d in sorted(CELLS_DIR.iterdir()):
        if not d.is_dir():
            continue
        pkg = _parse_yaml_like(d / "delivery.package")
        if not pkg:
            continue
        snap.append((
            d.name,
            pkg.get("status", "-"),
            pkg.get("version", "-"),
            pkg.get("last_gap_at") or "",
        ))
    return snap


# ---------- 维护模式判定 ----------
def check_maintenance_mode() -> bool:
    """若所有细胞均为 production_ready 且 state 中记录连续 7 天无新 gap，返回 True。"""
    snapshot = collect_snapshot()
    if not snapshot:
        return False
    if not all(s[1] == "production_ready" for s in snapshot):
        return False
    state_file = STATE_DIR / "last_gap_at.txt"
    if not state_file.exists():
        return False
    try:
        with open(state_file, "r") as f:
            last = f.read().strip()
        if not last:
            return False
        t = datetime.fromisoformat(last)
        return datetime.now() - t >= timedelta(days=7)
    except Exception:
        return False


def write_last_gap_now() -> None:
    """记录本次周期发现过 gap（用于维护模式判定）。"""
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    with open(STATE_DIR / "last_gap_at.txt", "w") as f:
        f.write(datetime.now().isoformat())


# ---------- 主流程 ----------
def run_cycle() -> None:
    """执行一次完整周期。"""
    GLASS_HOUSE.mkdir(parents=True, exist_ok=True)
    GAP_DIR.mkdir(parents=True, exist_ok=True)
    STATE_DIR.mkdir(parents=True, exist_ok=True)

    # 维护模式：直接更新日志并退出
    if check_maintenance_mode():
        update_live_log(
            ["**本周期**：进入维护模式，仅响应异常事件。无待处理细胞。"],
            collect_snapshot(),
            maintenance=True,
        )
        print("[evolution] MAINTENANCE MODE. No work this cycle.")
        return

    # 感知
    pending = sense()
    cycle_entries = [f"**本周期** {datetime.now().isoformat()}：感知到 {len(pending)} 个待完善细胞：{', '.join([p[0] for p in pending]) or '无'}."]
    gap_found = False

    for cell_name, cell_dir, pkg in pending:
        # 对标
        gap_path = benchmark(cell_name, cell_dir)
        cycle_entries.append(f"- **{cell_name}**：已生成对标报告 `glass_house/gap_analysis/{cell_name}_gap_analysis.md`")
        gap_found = True

        # 验证：仅对 ready_for_qa 执行验证并可能晋升
        if (pkg.get("status") or "").strip().lower() == "ready_for_qa":
            if run_verify(cell_name):
                set_production_ready(cell_name)
                announce_to_registry(cell_name)
                cycle_entries.append(f"  - 验证通过，已置为 production_ready 并写入注册中心。")
            else:
                cycle_entries.append(f"  - 验证未通过，请修正后再次运行周期。")

    if gap_found:
        write_last_gap_now()

    snapshot = collect_snapshot()
    update_live_log(cycle_entries, snapshot, maintenance=False)
    print("[evolution] cycle done. See glass_house/live_evolution_log.md")
    return


if __name__ == "__main__":
    os.chdir(ROOT)
    run_cycle()
