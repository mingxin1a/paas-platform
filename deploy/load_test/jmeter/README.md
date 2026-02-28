# JMeter 压测说明

本目录可放置 JMeter 测试计划（.jmx），与 Locust 互为补充。

## 核心场景

1. **网关健康**：GET /health，线程组 50，持续 60s。
2. **登录**：POST /api/auth/login，JSON body，取 token 后存入变量。
3. **细胞列表**：GET /api/v1/{cell}/customers|orders|...，Header Manager 带 Authorization、X-Tenant-Id、X-Request-ID。
4. **管理端**：GET /api/admin/cells、/api/admin/health-summary，需 Bearer token。

## 性能指标

- 核心接口 P95 响应时间 ≤ 300ms。
- 500 并发下成功率 ≥ 99.9%。
- 聚合报告中关注：Average、90th/95th Percentile、Error %、Throughput。

## 执行

```bash
jmeter -n -t performance_plan.jmx -l result.jtl -e -o report/
```

主压测脚本以 Locust 为准，见上级目录 `locustfile.py` 与 `run_performance_tests.py`。
