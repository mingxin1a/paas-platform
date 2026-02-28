# LIS 与 HIS 对接手册

**版本**：1.0 | **细胞**：LIS

## 1. 对接场景

- **HIS 发起检验申请**：HIS 调用 LIS POST /test-requests，Body：patientId、visitId、items（检验项目）。请求头需带 X-Tenant-Id。
- **样本与患者关联**：LIS 创建样本时传入 patientId、requestId，便于与 HIS 就诊、患者关联。
- **报告回传**：LIS 报告生成/审核后，HIS 可通过 GET /reports?sampleId=xxx 或 GET /reports/<reportId> 获取报告内容。

## 2. 接口兼容

- 统一使用 JSON、UTF-8；错误响应：code、message、requestId。
- 幂等：创建检验申请、样本、结果、报告均支持 X-Request-ID。

## 3. 数据与权限

- 多租户隔离（X-Tenant-Id）；检验师身份（X-User-Id）用于 LIS 侧结果/样本列表过滤。
