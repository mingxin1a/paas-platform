# 行业解决方案包索引

基于 SuperPaaS 细胞化架构的标准化行业解决方案，支持模块按需选配、灵活增减，不修改平台核心。

---

## 一、通用制造业解决方案

- **模块组合**：ERP + MES + WMS + SRM + TMS  
- **适用**：中小制造企业全流程管理（计划、生产、仓储、采购、物流一体化）  
- **文档目录**：[manufacturing/](manufacturing/)  
- **交付包构建**：`python scripts/build_solution_delivery.py --solution manufacturing`  
- **交付物**：`dist/Solution_Manufacturing_YYYYMMDD/` 及同名 zip  

---

## 二、通用贸易企业解决方案

- **模块组合**：CRM + ERP + WMS + SRM + OA  
- **适用**：贸易/流通企业进销存与协同一体化  
- **文档目录**：[trade/](trade/)  
- **交付包构建**：`python scripts/build_solution_delivery.py --solution trade`  
- **交付物**：`dist/Solution_Trade_YYYYMMDD/` 及同名 zip  

---

## 三、医疗行业解决方案

- **模块组合**：HIS + LIS + OA + ERP  
- **适用**：医院/医疗机构信息化，满足诊疗、检验、审批、物资与成本管理及医疗数据合规要求  
- **文档目录**：[healthcare/](healthcare/)  
- **交付包构建**：`python scripts/build_solution_delivery.py --solution healthcare`  
- **交付物**：`dist/Solution_Healthcare_YYYYMMDD/` 及同名 zip  
- **特别说明**：含《医疗行业合规适配说明》，验收时需合规项通过并签字  

---

## 四、各方案文档结构（统一）

| 文档 | 说明 |
|------|------|
| 01_行业痛点分析 | 行业典型痛点与对应能力 |
| 02_方案架构 | 细胞化架构、逻辑架构、数据流与集成点、部署建议 |
| 03_功能清单 | 各模块功能域与功能点、模块选配说明 |
| 04_部署方案 | 部署拓扑、环境与路由、交付物、资源建议 |
| 05_实施计划 | 阶段划分、关键里程碑、风险与应对 |
| 06_实施手册 | 实施前准备、部署步骤、配置要点、验收标准 |
| 07_验收清单 | 平台与模块验收项、必填/选填、自动化验收说明 |
| 08_成功案例模板 | 客户概况、痛点、方案范围、实施与验收、效果、评价（医疗含合规与脱敏） |
| 09_报价模板 | 方案范围、报价项、可选与扩展、条款说明 |

医疗方案额外包含：**08_合规适配说明**（患者隐私与脱敏、病历不可篡改与可审计、检验报告全流程等）、**10_报价模板**（含合规与等保支持项）。

---

## 五、构建与验收

- **构建**：在项目根目录执行 `python scripts/build_solution_delivery.py --solution <manufacturing|trade|healthcare>`，生成 `dist/Solution_<Solution>_YYYYMMDD/` 及 zip。
- **验收**：部署后执行 `python scripts/run_acceptance_test.py`（网关仅路由该方案所含 Cell），或分模块 `python scripts/run_module_acceptance.py <cell_id>`；人工核对对应《验收清单》及（医疗）《合规适配说明》。

---

**文档归属**：行业解决方案包 · 索引
