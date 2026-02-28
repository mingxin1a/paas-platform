-- TMS 细胞独立 Schema（工业/商用：运输订单、车辆、司机、轨迹、到货、费用、对账）
-- 司机信息（手机号/身份证）加密存储由应用层实现；操作日志留存≥1年
SET NAMES utf8mb4;
CREATE TABLE event_store (
  event_id BIGINT PRIMARY KEY AUTO_INCREMENT, aggregate_type VARCHAR(50) NOT NULL, aggregate_id VARCHAR(100) NOT NULL,
  event_type VARCHAR(100) NOT NULL, event_data JSON NOT NULL, event_version INT NOT NULL DEFAULT 1,
  occurred_on DATETIME(6) NOT NULL, recorded_by VARCHAR(100) NOT NULL, recorded_at DATETIME(6) NOT NULL,
  tenant_id VARCHAR(100) NOT NULL,
  INDEX idx_aggregate (aggregate_type, aggregate_id), INDEX idx_tenant_recorded (tenant_id, recorded_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
CREATE TABLE shipment_read_model (
  shipment_id VARCHAR(100) PRIMARY KEY, tenant_id VARCHAR(100) NOT NULL, owner_id VARCHAR(100),
  status TINYINT NOT NULL, created_at DATETIME(6) NOT NULL, updated_at DATETIME(6) NOT NULL,
  INDEX idx_tenant_status (tenant_id, status), INDEX idx_tenant_owner (tenant_id, owner_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS vehicle (
  vehicle_id VARCHAR(100) NOT NULL PRIMARY KEY, tenant_id VARCHAR(100) NOT NULL, plate_no VARCHAR(32) NOT NULL,
  model VARCHAR(100), status TINYINT DEFAULT 1, created_at DATETIME(6) NOT NULL,
  INDEX idx_tenant (tenant_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS driver (
  driver_id VARCHAR(100) NOT NULL PRIMARY KEY, tenant_id VARCHAR(100) NOT NULL, name VARCHAR(200) NOT NULL,
  phone_encrypted VARCHAR(500), id_no_encrypted VARCHAR(500), status TINYINT DEFAULT 1, created_at DATETIME(6) NOT NULL,
  INDEX idx_tenant (tenant_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS transport_track (
  track_id VARCHAR(100) NOT NULL PRIMARY KEY, tenant_id VARCHAR(100) NOT NULL, shipment_id VARCHAR(100) NOT NULL,
  lat VARCHAR(32), lng VARCHAR(32), node_name VARCHAR(200), occurred_at DATETIME(6) NOT NULL,
  INDEX idx_shipment (shipment_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS delivery_confirm (
  confirm_id VARCHAR(100) NOT NULL PRIMARY KEY, tenant_id VARCHAR(100) NOT NULL, shipment_id VARCHAR(100) NOT NULL,
  status VARCHAR(20) NOT NULL, signed_at DATETIME(6), created_at DATETIME(6) NOT NULL,
  INDEX idx_shipment (shipment_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS transport_cost (
  cost_id VARCHAR(100) NOT NULL PRIMARY KEY, tenant_id VARCHAR(100) NOT NULL, shipment_id VARCHAR(100) NOT NULL,
  amount_cents BIGINT NOT NULL, currency VARCHAR(10) DEFAULT 'CNY', cost_type VARCHAR(50), created_at DATETIME(6) NOT NULL,
  INDEX idx_shipment (shipment_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS logistics_reconciliation (
  reconciliation_id VARCHAR(100) NOT NULL PRIMARY KEY, tenant_id VARCHAR(100) NOT NULL,
  period_start DATE, period_end DATE, total_amount_cents BIGINT, status VARCHAR(20), created_at DATETIME(6) NOT NULL,
  INDEX idx_tenant_period (tenant_id, period_start)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE audit_log (
  log_id BIGINT PRIMARY KEY AUTO_INCREMENT, tenant_id VARCHAR(100) NOT NULL, user_id VARCHAR(100) NOT NULL,
  operation_type VARCHAR(50) NOT NULL, operation_result TINYINT NOT NULL, trace_id VARCHAR(64), occurred_at DATETIME(6) NOT NULL,
  INDEX idx_tenant_user_time (tenant_id, user_id, occurred_at), INDEX idx_trace_id (trace_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
