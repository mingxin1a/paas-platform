# SRM 供应商管理指南

**版本**：1.0 | **细胞**：SRM

## 1. 供应商管理流程

1. **供应商准入**：创建供应商（POST /suppliers）→ 准入审核（可扩展 onboarding 状态与审批接口）。
2. **供应商评估**：对已准入供应商进行评分与维度评估（POST /evaluations）。
3. **采购需求**：创建采购需求（Schema 支持 owner_id，采购专员仅看自己负责的供应商）。
4. **询报价**：创建询价单（POST /rfqs）→ 供应商提交报价（POST /quotes，幂等）。
5. **采购订单**：创建采购订单（POST /purchase-orders），关联供应商。
6. **对账与评级**：供应商对账、评级（Schema 已定义，接口可扩展）。

## 2. 接口说明

### 2.1 供应商

- **列表**：GET /suppliers
- **详情**：GET /suppliers/<supplier_id>
- **创建**：POST /suppliers，Body：`{"name":"供应商名称","code":"SUP001","contact":"联系人"}`，头带 X-Request-ID。

### 2.2 询价单（RFQ）

- **列表**：GET /rfqs?page=1&pageSize=20
- **创建**：POST /rfqs，Body：`{"demandId":""}`，头带 X-Request-ID（幂等）。

### 2.3 报价

- **列表**：GET /quotes?rfqId=xxx&page=1&pageSize=20
- **提交**：POST /quotes，Body：`{"rfqId":"","supplierId":"","amountCents":10000,"currency":"CNY","validUntil":"2024-02-01"}`，头带 X-Request-ID（幂等）。若询价单不存在，返回商用提示「询价单不存在」。

### 2.4 供应商评估

- **列表**：GET /evaluations?supplierId=xxx&page=1&pageSize=20
- **创建**：POST /evaluations，Body：`{"supplierId":"","score":85,"dimension":"质量","comment":"备注"}`，头带 X-Request-ID。若供应商不存在，返回「供应商不存在，请先完成供应商准入」。

### 2.5 采购订单

- **列表/详情/创建/更新**：见 /purchase-orders 接口。

## 3. 数据权限

- 采购需求：采购专员仅能查看自己负责的供应商（owner_id 与 X-User-Id 关联，接口扩展时实现）。
- 报价：生产环境建议加密存储，展示时脱敏或按权限开放。

## 4. 商用化错误提示

- 报价时询价单不存在：`BUSINESS_RULE_VIOLATION`，「询价单不存在」。
- 评估时供应商不存在：`BUSINESS_RULE_VIOLATION`，「供应商不存在，请先完成供应商准入」。
- 幂等冲突：`IDEMPOTENT_CONFLICT`，「幂等冲突」。
