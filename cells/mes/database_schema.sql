-- MES 细胞独立 Schema（工业场景：BOM→计划→生产订单→领料→报工→生产入库→追溯）
-- 操作日志留存≥1年（工业数据留存），生产工艺数据加密存储由应用层/KMS 实现
SET NAMES utf8mb4;
CREATE TABLE event_store (
  event_id BIGINT PRIMARY KEY AUTO_INCREMENT, aggregate_type VARCHAR(50) NOT NULL, aggregate_id VARCHAR(100) NOT NULL,
  event_type VARCHAR(100) NOT NULL, event_data JSON NOT NULL, event_version INT NOT NULL DEFAULT 1,
  occurred_on DATETIME(6) NOT NULL, recorded_by VARCHAR(100) NOT NULL, recorded_at DATETIME(6) NOT NULL,
  tenant_id VARCHAR(100) NOT NULL,
  INDEX idx_aggregate (aggregate_type, aggregate_id), INDEX idx_tenant_recorded (tenant_id, recorded_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE work_order_read_model (
  work_order_id VARCHAR(100) PRIMARY KEY, tenant_id VARCHAR(100) NOT NULL, workshop_id VARCHAR(100),
  status TINYINT NOT NULL, created_at DATETIME(6) NOT NULL, updated_at DATETIME(6) NOT NULL,
  INDEX idx_tenant_status (tenant_id, status), INDEX idx_tenant_workshop (tenant_id, workshop_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 车间（数据权限：车间主任只看本车间订单）
CREATE TABLE IF NOT EXISTS workshop (
  workshop_id VARCHAR(100) NOT NULL PRIMARY KEY, tenant_id VARCHAR(100) NOT NULL, name VARCHAR(200) NOT NULL,
  created_at DATETIME(6) NOT NULL, INDEX idx_tenant (tenant_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- BOM（生产工艺数据可加密存储）
CREATE TABLE IF NOT EXISTS bom (
  bom_id VARCHAR(100) NOT NULL PRIMARY KEY, tenant_id VARCHAR(100) NOT NULL, product_sku VARCHAR(100) NOT NULL,
  version INT NOT NULL DEFAULT 1, routing_encrypted TEXT COMMENT '工艺路线加密存储',
  created_at DATETIME(6) NOT NULL, INDEX idx_tenant_product (tenant_id, product_sku)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
CREATE TABLE IF NOT EXISTS bom_component (
  line_id VARCHAR(100) NOT NULL PRIMARY KEY, bom_id VARCHAR(100) NOT NULL, material_sku VARCHAR(100) NOT NULL,
  quantity DECIMAL(18,6) NOT NULL, created_at DATETIME(6) NOT NULL, INDEX idx_bom (bom_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 生产计划
CREATE TABLE IF NOT EXISTS production_plan (
  plan_id VARCHAR(100) NOT NULL PRIMARY KEY, tenant_id VARCHAR(100) NOT NULL, plan_no VARCHAR(64) NOT NULL,
  product_sku VARCHAR(100) NOT NULL, planned_qty DECIMAL(18,6) NOT NULL, plan_date DATE,
  status TINYINT NOT NULL DEFAULT 1, created_at DATETIME(6) NOT NULL,
  INDEX idx_tenant_date (tenant_id, plan_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 生产订单（关联车间，数据权限）
CREATE TABLE IF NOT EXISTS production_order (
  order_id VARCHAR(100) NOT NULL PRIMARY KEY, tenant_id VARCHAR(100) NOT NULL, workshop_id VARCHAR(100) NOT NULL,
  plan_id VARCHAR(100), order_no VARCHAR(64) NOT NULL, product_sku VARCHAR(100) NOT NULL,
  quantity DECIMAL(18,6) NOT NULL, status TINYINT NOT NULL DEFAULT 1,
  created_at DATETIME(6) NOT NULL, updated_at DATETIME(6) NOT NULL,
  INDEX idx_tenant_workshop (tenant_id, workshop_id), INDEX idx_tenant_status (tenant_id, status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 领料单（防超领：已领数量≤应领数量）
CREATE TABLE IF NOT EXISTS material_issue (
  issue_id VARCHAR(100) NOT NULL PRIMARY KEY, tenant_id VARCHAR(100) NOT NULL, order_id VARCHAR(100) NOT NULL,
  material_sku VARCHAR(100) NOT NULL, required_qty DECIMAL(18,6) NOT NULL, issued_qty DECIMAL(18,6) NOT NULL DEFAULT 0,
  created_at DATETIME(6) NOT NULL, INDEX idx_order (order_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 报工（工序）
CREATE TABLE IF NOT EXISTS work_report (
  report_id VARCHAR(100) NOT NULL PRIMARY KEY, tenant_id VARCHAR(100) NOT NULL, order_id VARCHAR(100) NOT NULL,
  operation_code VARCHAR(100) NOT NULL, completed_qty DECIMAL(18,6) NOT NULL, report_at DATETIME(6) NOT NULL,
  created_at DATETIME(6) NOT NULL, INDEX idx_order (order_id), INDEX idx_tenant_order (tenant_id, order_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 生产入库（幂等：request_id）
CREATE TABLE IF NOT EXISTS production_inbound (
  inbound_id VARCHAR(100) NOT NULL PRIMARY KEY, tenant_id VARCHAR(100) NOT NULL, order_id VARCHAR(100) NOT NULL,
  warehouse_id VARCHAR(100), quantity DECIMAL(18,6) NOT NULL, lot_number VARCHAR(100), serial_numbers TEXT,
  created_at DATETIME(6) NOT NULL, idempotent_key VARCHAR(128) UNIQUE,
  INDEX idx_order (order_id), INDEX idx_idem (idempotent_key)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 生产追溯（批次/序列号）
CREATE TABLE IF NOT EXISTS production_trace (
  trace_id VARCHAR(100) NOT NULL PRIMARY KEY, tenant_id VARCHAR(100) NOT NULL, order_id VARCHAR(100) NOT NULL,
  lot_number VARCHAR(100), serial_number VARCHAR(100), product_sku VARCHAR(100) NOT NULL,
  quantity DECIMAL(18,6) NOT NULL, created_at DATETIME(6) NOT NULL,
  INDEX idx_lot (tenant_id, lot_number), INDEX idx_serial (tenant_id, serial_number), INDEX idx_order (order_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 操作日志（工业留存≥1年）
CREATE TABLE audit_log (
  log_id BIGINT PRIMARY KEY AUTO_INCREMENT, tenant_id VARCHAR(100) NOT NULL, user_id VARCHAR(100) NOT NULL,
  operation_type VARCHAR(50) NOT NULL, operation_result TINYINT NOT NULL, trace_id VARCHAR(64), occurred_at DATETIME(6) NOT NULL,
  resource_type VARCHAR(50), resource_id VARCHAR(100),
  INDEX idx_tenant_user_time (tenant_id, user_id, occurred_at), INDEX idx_trace_id (trace_id),
  INDEX idx_occurred (occurred_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT '工业场景操作日志，留存≥1年';
