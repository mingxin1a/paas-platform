# EMS 行业合规指南

**版本**：1.0 | **细胞**：EMS | **适用**：能耗管理行业合规

## 工业能耗规范适配

- **计量单位**：支持 kWh 等，接口字段 unit。
- **统计周期**：按日（day）、周（week）、月（month）、年（year）聚合，GET /stats?period=xxx。
- **数据留存**：能耗数据保留不少于 3 年，由配置项 energyDataRetentionDays（默认 1095）保障；持久化后由备份与归档策略落实。

## 监管要求

- **数据导出**：GET /export?fromDate=&toDate=&limit= 支持按时间范围导出，供监管报送或审计。
- **多租户**：企业能耗数据按 tenant_id 隔离，不跨租户访问。

## 配置与接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /config/retention | 数据留存天数（≥3年） |
| GET | /stats | 按 period 统计 |
| GET | /alerts | 预警列表 |
| GET | /export | 导出能耗数据 |

**详细**：见 `cells/ems/docs/EMS能耗合规指南.md`、`EMS数据上报手册（模拟）.md`。
