# EMS 行业级测试报告

**版本**：1.0 | **细胞**：EMS | **测试类型**：合规 / 功能 / 安全

## 1. 合规测试

| 用例 | 说明 | 预期 |
|------|------|------|
| 数据留存配置 | GET /config/retention 返回 energyDataRetentionDays ≥ 1095 | 通过 |
| 能耗数据导出 | GET /export?fromDate=&toDate= 返回时间范围内记录，符合监管报送 | 通过 |
| 多租户隔离 | 不同 X-Tenant-Id 仅能访问本租户能耗数据 | 通过 |

## 2. 功能测试

| 用例 | 说明 | 预期 |
|------|------|------|
| 能耗采集幂等 | POST /consumption-records 相同 X-Request-ID 返回 409 或已创建记录 | 通过 |
| 按日/周/月/年统计 | GET /stats?period=day\|week\|month\|year 返回聚合结果 | 通过 |
| 能耗预警 | POST /alerts 创建预警；GET /alerts 列表 | 通过 |
| 分页列表 | GET /consumption-records?page=1&pageSize=20 分页正确 | 通过 |

## 3. 安全测试

| 用例 | 说明 | 预期 |
|------|------|------|
| 租户隔离 | 请求无 X-Tenant-Id 时使用 default，不同租户数据不可见 | 通过 |
| 验签开关 | CELL_VERIFY_SIGNATURE=1 时网关验签 | 通过 |
| 审计日志 | 创建/查询操作记录人性化审计 | 通过 |
