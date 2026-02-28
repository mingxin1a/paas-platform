# 孵化器行动日志

**原则**：完全自主、玻璃房透明；所有孵化与进化动作在此记录。

---

## 2026-02-24 孵化器启动与首轮交付

### 治理与标准

- 创建 **glass_house/incubator_manifest.md**：细胞 = 独立项目（docker-compose、README、dist）、自发现与孵化（外部/内部）、持续知识进化、全栈自愈、人工介入队列。
- 创建 **glass_house/human_intervention_queue.md**：待处理/已处理模板，供 monitor 与 ai_agent 写入严重问题。

### 细胞独立交付标准（CRM / ERP / WMS）

- **CRM**：cells/crm/Dockerfile（上下文为本目录）、docker-compose.yml、README.md、dist/PACKAGE.md。可在本目录执行 `docker compose up -d` 一键启动。
- **ERP**：cells/erp/ 同上，端口 8002。
- **WMS**：cells/wms/ 同上，端口 8003。

### 外部孵化：HRM 细胞

- **决策**：基于内置知识，人力资源（OrangeHRM 等）为稳定 SaaS 领域，创建新细胞 **cells/hrm/**。
- **对标**：参考 OrangeHRM 通用能力（员工、部门、请假）；**智能对标血肉化**：用 SuperPaaS 架构重写（独立 Schema、仅网关交互、事件域 hrm、ai_agent + auto_healing）。
- **交付**：cell_profile.md、api_contract.yaml、database_schema.sql、auto_healing.yaml、ai_agent.py、src/store.py、src/app.py（/health、/employees、/departments、/leave-requests）、delivery.package（building）、completion.manifest、Dockerfile、docker-compose.yml、README.md、dist/PACKAGE.md、docs/用户手册.md、docs/部署指南.md、LICENSE。
- **状态**：HRM 为骨架（building），待后续“血肉化”与 verify 通过后置为 production_ready。
- **合规**：未引入任何外部专有代码；符合《00_最高宪法》与《01_核心法律》。

---

## 后续周期（示例）

- **每周业界对标扫描**：为各细胞识别可新增功能（如 WMS 增加 AI 库位推荐），安全注入并更新 delivery.package 与用户手册。
- **内部孵化**：当某细胞子模块复杂度或边界达到阈值时，生成《内部孵化提案》并执行拆分。
- **自愈**：已知问题走 auto_healing；新问题生成自愈方案并提交修复；严重问题写入 human_intervention_queue.md。
