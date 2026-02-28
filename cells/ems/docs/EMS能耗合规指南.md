# EMS 能耗合规指南

**版本**：1.0 | **细胞**：EMS

## 1. 工业能耗规范适配

- **计量单位**：支持 kWh 等，接口字段 unit。
- **统计周期**：支持按日（day）、周（week）、月（month）、年（year）聚合，GET /stats?period=xxx。
- **数据留存**：能耗数据保留不少于 3 年，由配置项 energyDataRetentionDays 保障（模拟）；持久化落地后由备份与归档策略实现。
- **操作审计**：所有关键操作（采集、预警、导出）写入不可篡改审计日志，GET /audit-logs 可查询。

## 2. 监管要求

- **数据导出**：GET /export?fromDate=&toDate=&limit= 支持按时间范围导出，供监管报送或审计。
- **多租户**：企业能耗数据按 tenant_id 隔离，不跨租户访问。
- **全流程闭环**：能耗采集→能耗统计→能耗分析→能耗预警→能耗报表→节能建议，均通过 PaaS 标准化接口对外，无跨细胞代码耦合。

## 3. 接口说明

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /config/retention | 数据留存天数（≥3年） |
| GET/POST | /consumption-records | 能耗采集 |
| GET | /stats | 按 period 统计 |
| GET | /analysis | 能耗分析（趋势、异常） |
| GET/POST | /alerts | 预警列表与创建 |
| GET | /reports | 能耗报表 |
| GET | /suggestions | 节能建议 |
| GET | /export | 导出能耗数据 |
| GET | /audit-logs | 操作审计日志（不可篡改） |
