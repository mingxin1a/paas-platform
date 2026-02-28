-- EMS 细胞独立 Schema（行业合规：能耗采集→统计→分析→预警→报表；数据留存≥3年）
-- 能耗数据加密存储由应用层/KMS 实现；多租户隔离
SET NAMES utf8mb4;
CREATE TABLE event_store (
  event_id BIGINT PRIMARY KEY AUTO_INCREMENT, aggregate_type VARCHAR(50) NOT NULL, aggregate_id VARCHAR(100) NOT NULL,
  event_type VARCHAR(100) NOT NULL, event_data JSON NOT NULL, event_version INT NOT NULL DEFAULT 1,
  occurred_on DATETIME(6) NOT NULL, recorded_by VARCHAR(100) NOT NULL, recorded_at DATETIME(6) NOT NULL,
  tenant_id VARCHAR(100) NOT NULL,
  INDEX idx_aggregate (aggregate_type, aggregate_id), INDEX idx_tenant_recorded (tenant_id, recorded_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE consumption_read_model (
  record_id VARCHAR(100) NOT NULL PRIMARY KEY, tenant_id VARCHAR(100) NOT NULL, meter_id VARCHAR(100) NOT NULL,
  value_encrypted TEXT COMMENT '能耗值可加密', unit VARCHAR(20) NOT NULL DEFAULT 'kWh',
  record_time DATETIME(6) NOT NULL, created_at DATETIME(6) NOT NULL,
  INDEX idx_tenant_recorded (tenant_id, record_time), INDEX idx_tenant_meter (tenant_id, meter_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT '能耗数据留存≥3年，符合工业能耗监管';

CREATE TABLE IF NOT EXISTS energy_alert (
  alert_id VARCHAR(100) NOT NULL PRIMARY KEY, tenant_id VARCHAR(100) NOT NULL, meter_id VARCHAR(100),
  alert_type VARCHAR(50) NOT NULL COMMENT 'over_threshold|anomaly|low_power',
  threshold_value DECIMAL(18,4), actual_value DECIMAL(18,4), occurred_at DATETIME(6) NOT NULL,
  acknowledged TINYINT NOT NULL DEFAULT 0,
  INDEX idx_tenant_occurred (tenant_id, occurred_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE audit_log (
  log_id BIGINT PRIMARY KEY AUTO_INCREMENT, tenant_id VARCHAR(100) NOT NULL, user_id VARCHAR(100) NOT NULL,
  operation_type VARCHAR(50) NOT NULL, operation_result TINYINT NOT NULL, trace_id VARCHAR(64), occurred_at DATETIME(6) NOT NULL,
  INDEX idx_tenant_user_time (tenant_id, user_id, occurred_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
