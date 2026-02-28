# 批次3 垂直行业 Cell 交付说明（EMS/PLM/HIS/LIS/LIMS）

**版本**：1.0 | **状态**：基础商用可落地

## 1. 交付范围

| 细胞 | 核心业务流程闭环 | 行业合规 | 交付物 |
|------|------------------|----------|--------|
| **EMS** | 能耗采集→统计→分析→预警→报表→节能建议 | 工业能耗监管、数据留存≥3年、操作审计 | 测试/部署/交付手册/合规指南 |
| **PLM** | 产品设计→BOM版本→工艺→变更→文档→图纸 | 研发管理、版本追溯、变更可审计 | 同上 |
| **HIS** | 患者→挂号→就诊→处方→收费→住院→病历 | 医疗隐私、脱敏、不可篡改审计 | 同上 |
| **LIS** | 检验申请→样本接收→结果录入→报告生成→审核→发布 | 医疗检验规范、报告可追溯 | 同上 |
| **LIMS** | 样品接收→任务分配→数据录入→报告→审核→归档 | 实验室合规、数据留存≥5年、溯源 | 同上 |

## 2. 细胞化架构遵守情况

- 各模块**完全独立**，无跨细胞代码耦合。
- 仅通过 **PaaS 层标准化接口**（X-Tenant-Id、X-Request-ID、事件总线 POST /api/events）与平台或其它细胞联动。
- EMS/PLM 已接入事件发布（event_publisher），可向平台事件总线发布领域事件。

## 3. 合规适配摘要

### EMS（工业能耗）
- 能耗数据留存≥3年（配置项 `EMS_ENERGY_DATA_RETENTION_DAYS`）。
- 操作审计日志不可篡改（GET /audit-logs）。
- 导出接口满足监管报送（GET /export）。

### PLM（研发管理）
- BOM 版本、变更记录可追溯；文档/图纸与产品关联。
- 操作审计日志（GET /audit-logs）。

### HIS（医疗）
- 患者信息脱敏（姓名、身份证号）；病历仅追加不可篡改。
- 操作审计日志（GET /audit-logs）；挂号/收费幂等。

### LIS（检验）
- 样本接收、报告审核、报告发布分步可追溯；报告状态：0 草稿 / 1 已审核 / 2 已发布。
- 操作审计日志（GET /audit-logs）。

### LIMS（实验室）
- 实验数据留存≥5年（配置项 `LIMS_LAB_DATA_RETENTION_DAYS`）。
- 样品接收、报告审核、报告归档；数据溯源（GET /trace）。

## 4. 部署与测试

- **部署**：各细胞已纳入 `deploy/docker-compose.yml`、`deploy/gateway_route_spec.yaml`；端口 EMS 8010、PLM 8009、HIS 8011、LIS 8012、LIMS 8013。
- **单细胞测试**：`pytest cells/<cell>/tests/unit/ -v`（如 `cells/ems/tests/unit/`）。
- **核心业务流程联测**：`python deploy/core_business_flow_tests.py`（含 EMS/PLM/HIS/LIS/LIMS 流程）。

## 5. 交付物清单（每细胞）

| 交付物 | 路径示例 |
|--------|-----------|
| 基础测试用例 | `cells/ems/tests/unit/test_ems_app.py` 等 |
| 部署配置 | `cells/ems/Dockerfile`、`docker-compose.yml`、网关路由 |
| 交付手册 | `cells/ems/docs/EMS商用交付手册（能耗版）.md` 等 |
| 合规适配说明 | `cells/ems/docs/EMS能耗合规指南.md`、HIS/LIS/LIMS 合规文档 |
| API 契约 | `cells/ems/api_contract.yaml` |
| completion.manifest | `cells/ems/completion.manifest` |

## 6. 接口速览（各细胞）

- **EMS**：/health, /config/retention, /consumption-records, /stats, /analysis, /alerts, /reports, /suggestions, /export, /audit-logs
- **PLM**：/health, /products, /boms, /change-records, /documents, /process-routes, /drawings, /audit-logs
- **HIS**：/health, /patients, /visits, /registration, /prescriptions, /charges, /inpatients, /medical-records, /orders, /audit-logs
- **LIS**：/health, /test-requests, /samples, /samples/:id/receive, /results, /reports, /reports/:id/review, /reports/:id/publish, /audit-logs
- **LIMS**：/health, /config/retention, /samples, /samples/:id/receive, /tasks, /experiment-data, /reports, /reports/:id/review, /reports/:id/archive, /trace
