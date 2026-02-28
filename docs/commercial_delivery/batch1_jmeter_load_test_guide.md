# Batch1 Core APIs - JMeter Load Test Guide

**Version**: 1.0  
**Target**: Single API >=500 TPS, response time <=300ms (P95)  
**Scope**: CRM, ERP, OA, SRM cells (via gateway or direct)

## 1. Environment

- Tool: Apache JMeter 5.x
- Headers: X-Tenant-Id (required); X-Request-ID for write (unique)

## 2. Core APIs & Targets

| Cell | Method | Path (relative) | TPS | P95 |
|------|--------|-----------------|-----|-----|
| CRM | GET | /api/v1/crm/health | >=500 | <=50ms |
| CRM | GET | /api/v1/crm/customers?page=1&pageSize=20 | >=500 | <=300ms |
| CRM | GET | /api/v1/crm/reports/sales-forecast | >=500 | <=300ms |
| ERP | GET | /api/v1/erp/health | >=500 | <=50ms |
| ERP | GET | /api/v1/erp/pp/cost-summary | >=500 | <=300ms |
| OA | GET | /api/v1/oa/health | >=500 | <=50ms |
| OA | GET | /api/v1/oa/tasks | >=500 | <=300ms |
| SRM | GET | /api/v1/srm/health | >=500 | <=50ms |
| SRM | GET | /api/v1/srm/bidding/projects | >=500 | <=300ms |

## 3. Thread Group

- Threads: 500
- Ramp-up: 60s
- Loop: 5 min or forever

## 4. Pass Criteria

- Per-interface TPS >= 500, P95 <= 300ms, Error rate 0%.

## 5. Cell Direct (no gateway)

- CRM 8001, ERP 8002, OA 8005, SRM 8008 - e.g. GET http://localhost:8001/health
