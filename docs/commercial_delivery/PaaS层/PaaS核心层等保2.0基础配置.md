# PaaS 核心层等保 2.0 基础配置

**适用范围**：平台网关、治理、监控、审计；细胞独立部署，仅通过 HTTP 调用 PaaS 核心。

---

## 1. 身份与访问

| 项 | 配置/实现 |
|----|-----------|
| 认证 | 网关 `/api/auth/login` 统一登录，Token 下发；细胞经网关代理，不直连认证 |
| 权限 | 网关维护用户 allowedCells；管理端可配置细胞级、租户级权限 |
| 会话 | Token 有效期可配置；登出即失效（服务端可维护黑名单） |

---

## 2. 审计与不可篡改

| 项 | 配置/实现 |
|----|-----------|
| 操作日志 | `platform_core/core/gateway/audit_log.py`：仅追加写入 `glass_house/operation_audit.log` |
| 不可篡改 | 每条记录含 `lineHash`（SHA256 前 16 字符），事后可校验完整性 |
| 安全审计 | 验签失败等安全事件写入 `glass_house/security_audit.log` |

---

## 3. 敏感数据

| 项 | 配置/实现 |
|----|-----------|
| 传输 | 生产环境 HTTPS（部署层 Nginx/Ingress 配置） |
| 存储 | `platform_core/core/sensitive.py`：`encrypt_at_rest`/`decrypt_at_rest`（需配置 `SENSITIVE_AES_KEY`） |
| 展示 | 脱敏：`mask_phone`、`mask_id_no`、`mask_email` 等；细胞可选用或自实现 |

---

## 4. 安全通信与边界

| 项 | 配置/实现 |
|----|-----------|
| 网关入口 | 仅网关对外；细胞内网或 Sidecar 暴露，不直接对外 |
| 验签 | 细胞可选 `CELL_VERIFY_SIGNATURE=1`，网关与细胞间签名防篡改 |
| 限流 | 网关 `rate_limit` 模块；可配置 IP/Token 维度 |

---

## 5. 环境变量（等保相关）

| 变量 | 说明 |
|------|------|
| `SENSITIVE_AES_KEY` / `KMS_DATA_KEY` | 敏感字段存储加密密钥（base64 或明文，建议 KMS 注入） |
| `GATEWAY_APP_KEYS` | 应用密钥，格式 `cell_id:key` 或单 key |
| `CELL_VERIFY_SIGNATURE` | 细胞端设为 `1` 启用网关请求验签 |
| `SUPERPAAS_ROOT` | 项目根目录，审计日志写入 `{ROOT}/glass_house` |

---

**文档归属**：商用交付 · PaaS 层
