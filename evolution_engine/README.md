# 自主进化引擎

SuperPaaS「永不停止的自主进化引擎」单次周期实现。  
每 24 小时执行一次即可逼近「完美交付状态」。

## 运行方式

**单次周期（推荐）**

```bash
# 项目根目录下
python evolution_engine/evolution_engine.py
```

或（Linux/Mac/Git Bash）：

```bash
./run.sh evolution
# 或
./scripts/run_evolution_cycle.sh
```

**每 24 小时自动执行**

- **Linux / Mac**：cron  
  `0 0 * * * cd /path/to/paas-platform && ./scripts/run_evolution_cycle.sh`
- **Windows**：任务计划程序，每日 0:00 运行  
  `python C:\path\to\pass-platform\evolution_engine\evolution_engine.py`  
  工作目录设为项目根目录。

## 周期内步骤

1. **感知**：扫描 `cells/*/delivery.package`，选出 `status` 为 `building` 或 `ready_for_qa` 的细胞。
2. **对标**：为每个待完善细胞生成 `glass_house/gap_analysis/{CELL_NAME}_gap_analysis.md`（业界对标与可实现性）。
3. **进化**：仅对符合《00_最高宪法》与《01_核心法律》的项推进；实际代码与文档在 `cells/{CELL_NAME}/` 内由人工或后续 AI 完成。
4. **验证**：对 `ready_for_qa` 细胞执行 `verify_delivery`；通过则置为 `production_ready` 并写入 `glass_house/state/registry.json`。
5. **透明化**：更新 `glass_house/live_evolution_log.md` 与细胞状态快照。

## 维护模式

当**所有细胞**均为 `production_ready`，且**连续 7 天**无新 gap（即 7 天内没有出现 `building`/`ready_for_qa`）时，引擎进入维护模式：本周期仅更新日志并退出，仅响应异常事件。

## 约束

- **永不联网**：对标与知识仅来自本地文档与内置规则。
- **永不越界**：不增加违反架构原则的修改。
- **自我终止**：满足上述条件后进入维护模式。

## 验证单个细胞

```bash
./run.sh verify crm
# 或
./scripts/verify_delivery.sh crm
# 或
python evolution_engine/verify_delivery.py crm
```

退出码 0 表示通过。
