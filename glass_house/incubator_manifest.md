# SuperPaaS 数字创业孵化器 - 治理总纲

**角色**：孵化器总负责人 + 所有细胞的联合创始人  
**使命**：让 SuperPaaS 成为永续进化、自我繁衍的 SaaS 生态系统。  
**运行法则**：完全自主、7×24；玻璃房透明；《00_【最高宪法】》至上。

---

## 1. 细胞 = 独立项目（交付标准）

每个 `cells/{name}/` 必须满足：

| 项 | 要求 |
|----|------|
| **docker-compose.yml** | 在细胞目录内可一键启动（`docker compose up -d`），不依赖平台仓库其他路径。 |
| **README.md** | 说明如何本地运行（Python 直接运行 / Docker）、如何通过网关对接。 |
| **dist/** | 生产级安装包或构建说明（如 `dist/PACKAGE.md` + 发布时生成的 tarball）。 |
| **独立性** | 仅通过 PaaS 网关与平台/其他细胞交互，不直接依赖其他细胞代码或库。 |
| **合规** | 符合《00_最高宪法》与《01_核心法律》；含 delivery.package、ai_agent.py、auto_healing.yaml。 |

验收：在细胞目录执行 `docker compose up -d` 或 `python src/app.py` 可运行；`./run.sh verify {name}` 或 `./scripts/verify_delivery.sh {name}` 通过。

---

## 2. 自发现与孵化新细胞

### 2.1 外部孵化

- **触发**：基于内置知识识别新兴/稳定 SaaS 领域（如 OrangeHRM→HRM、Moodle→LMS、Odoo 模块等）。
- **流程**：创建 `cells/{new_name}/`，包含 src/、docker-compose.yml、delivery.package、api_contract.yaml、cell_profile.md、ai_agent.py、auto_healing.yaml、README.md、dist/。
- **实现**：智能对标血肉化——参考业界产品能力，用 SuperPaaS 架构（网关、独立 Schema、事件）重写，禁止直接拷贝外部专有代码。
- **记录**：在 glass_house 记录《外部孵化：{name} 细胞创建》及对标来源。

### 2.2 内部孵化

- **触发**：监控现有细胞复杂度（如某子模块代码量 > 10k 行或领域边界清晰可拆）。
- **流程**：生成《内部孵化提案：从 {parent} 拆分 {new_cell}》，经孵化器策略批准后执行。
- **执行**：迁移代码、数据模型、API 契约至 `cells/{new_cell}/`；父细胞保留网关转发或事件订阅；更新 delivery.package 与文档。
- **记录**：glass_house 记录提案与迁移结果。

---

## 3. 持续知识进化

- **周期**：每周（或按 cron 调度）对每个细胞执行一次。
- **业界对标扫描**：基于行业实践（Gartner、SaaS 趋势、开源路线图）识别可新增能力。
- **安全注入**：在不破坏现有架构与契约的前提下，为细胞增加新功能（例如 WMS 增加「AI 库位推荐」、CRM 增加「智能线索评分」）。
- **交付**：更新 delivery.package、用户手册、必要时 api_contract.yaml；变更写入 glass_house。

---

## 4. 全栈自愈运维

| 环节 | 动作 |
|------|------|
| **问题发现** | platform_core/core/monitor 分析业务与系统指标；各细胞 ai_agent.py 监听应用日志。 |
| **已知问题** | 命中 auto_healing.yaml 规则则按规则修复（如重启、重试、降级）。 |
| **新问题** | 生成《自愈方案.md》，自动提交修复（如 SQL 优化、配置调整）；可走 PR 流程。 |
| **严重问题** | 写入 **glass_house/human_intervention_queue.md**，等待人工介入。 |

---

## 5. 玻璃房记录

- **live_evolution_log.md**：进化与部署状态、细胞列表。
- **human_intervention_queue.md**：待人工处理事件队列。
- **incubator_actions.log**（或周期日志）：孵化、对标、自愈动作记录。
- 所有孵化/修改不得违反《00_【最高宪法】》；若有冲突，以宪法为准并记录裁决。

---

## 6. 当前孵化器状态

- **已达标细胞**（独立 Dockerfile + docker-compose + README + dist 说明）：crm, erp, wms。
- **外部孵化**：已创建 **cells/hrm/**（人力资源管理，对标 OrangeHRM，SuperPaaS 架构重写），当前为 building 骨架，verify_delivery 已通过。
- **待达标**：mes, tms, srm, oa, plm, ems, his, lis, lims 在进化为 production_ready 时同步补齐独立项目标准。
- **行动日志**：glass_house/incubator_actions.log.md。
