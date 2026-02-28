SET NAMES utf8mb4;
CREATE TABLE event_store (
  event_id BIGINT PRIMARY KEY AUTO_INCREMENT, aggregate_type VARCHAR(50) NOT NULL, aggregate_id VARCHAR(100) NOT NULL,
  event_type VARCHAR(100) NOT NULL, event_data JSON NOT NULL, event_version INT NOT NULL DEFAULT 1,
  occurred_on DATETIME(6) NOT NULL, recorded_by VARCHAR(100) NOT NULL, recorded_at DATETIME(6) NOT NULL,
  tenant_id VARCHAR(100) NOT NULL,
  INDEX idx_aggregate (aggregate_type, aggregate_id), INDEX idx_tenant_recorded (tenant_id, recorded_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
CREATE TABLE inventory_read_model (
  sku_id VARCHAR(100) NOT NULL, warehouse_id VARCHAR(100) NOT NULL, tenant_id VARCHAR(100) NOT NULL,
  quantity BIGINT NOT NULL, updated_at DATETIME(6) NOT NULL,
  PRIMARY KEY (tenant_id, warehouse_id, sku_id), INDEX idx_tenant_updated (tenant_id, updated_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
CREATE TABLE inbound_order_read_model (
  order_id VARCHAR(100) PRIMARY KEY, tenant_id VARCHAR(100) NOT NULL, warehouse_id VARCHAR(100) NOT NULL,
  status TINYINT NOT NULL COMMENT '1-草稿 2-收货中 3-已上架 4-关闭', created_at DATETIME(6) NOT NULL, updated_at DATETIME(6) NOT NULL,
  INDEX idx_tenant_status (tenant_id, status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
CREATE TABLE inbound_order_line (
  line_id VARCHAR(100) PRIMARY KEY, order_id VARCHAR(100) NOT NULL, tenant_id VARCHAR(100) NOT NULL,
  sku_id VARCHAR(100) NOT NULL, quantity BIGINT NOT NULL, received_quantity BIGINT NOT NULL DEFAULT 0, lot_number VARCHAR(100),
  INDEX idx_order (order_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
CREATE TABLE outbound_order_read_model (
  order_id VARCHAR(100) PRIMARY KEY, tenant_id VARCHAR(100) NOT NULL, warehouse_id VARCHAR(100) NOT NULL,
  status TINYINT NOT NULL COMMENT '1-草稿 2-拣货中 3-已发货 4-关闭', created_at DATETIME(6) NOT NULL, updated_at DATETIME(6) NOT NULL,
  INDEX idx_tenant_status (tenant_id, status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
CREATE TABLE outbound_order_line (
  line_id VARCHAR(100) PRIMARY KEY, order_id VARCHAR(100) NOT NULL, tenant_id VARCHAR(100) NOT NULL,
  sku_id VARCHAR(100) NOT NULL, quantity BIGINT NOT NULL, picked_quantity BIGINT NOT NULL DEFAULT 0,
  INDEX idx_order (order_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
CREATE TABLE location_read_model (
  location_id VARCHAR(100) PRIMARY KEY, tenant_id VARCHAR(100) NOT NULL, warehouse_id VARCHAR(100) NOT NULL,
  zone_code VARCHAR(50), aisle VARCHAR(20), level VARCHAR(20), position VARCHAR(20), status TINYINT NOT NULL DEFAULT 1 COMMENT '1-可用 2-占用 3-禁用',
  INDEX idx_tenant_warehouse (tenant_id, warehouse_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
CREATE TABLE lot_tracking (
  lot_id VARCHAR(100) PRIMARY KEY, tenant_id VARCHAR(100) NOT NULL, warehouse_id VARCHAR(100) NOT NULL, location_id VARCHAR(100),
  sku_id VARCHAR(100) NOT NULL, lot_number VARCHAR(100) NOT NULL, quantity BIGINT NOT NULL,
  production_date DATE, expiry_date DATE, created_at DATETIME(6) NOT NULL,
  INDEX idx_tenant_sku (tenant_id, sku_id), INDEX idx_lot (tenant_id, lot_number)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
CREATE TABLE audit_log (
  log_id BIGINT PRIMARY KEY AUTO_INCREMENT, tenant_id VARCHAR(100) NOT NULL, user_id VARCHAR(100) NOT NULL,
  operation_type VARCHAR(50) NOT NULL, operation_result TINYINT NOT NULL, trace_id VARCHAR(64), occurred_at DATETIME(6) NOT NULL,
  INDEX idx_tenant_user_time (tenant_id, user_id, occurred_at), INDEX idx_trace_id (trace_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 工业/商用：调拨、盘点、库存冻结、效期、库位权限、序列号追溯
CREATE TABLE IF NOT EXISTS transfer_order (
  transfer_id VARCHAR(100) NOT NULL PRIMARY KEY, tenant_id VARCHAR(100) NOT NULL,
  from_warehouse_id VARCHAR(100) NOT NULL, to_warehouse_id VARCHAR(100) NOT NULL,
  sku_id VARCHAR(100) NOT NULL, quantity BIGINT NOT NULL, status TINYINT NOT NULL DEFAULT 1,
  created_at DATETIME(6) NOT NULL, idempotent_key VARCHAR(128) UNIQUE,
  INDEX idx_tenant_status (tenant_id, status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS cycle_count (
  count_id VARCHAR(100) NOT NULL PRIMARY KEY, tenant_id VARCHAR(100) NOT NULL, warehouse_id VARCHAR(100) NOT NULL,
  sku_id VARCHAR(100) NOT NULL, location_id VARCHAR(100), book_quantity BIGINT NOT NULL, count_quantity BIGINT,
  count_at DATETIME(6), created_at DATETIME(6) NOT NULL,
  INDEX idx_tenant_warehouse (tenant_id, warehouse_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS inventory_freeze (
  freeze_id VARCHAR(100) NOT NULL PRIMARY KEY, tenant_id VARCHAR(100) NOT NULL, warehouse_id VARCHAR(100) NOT NULL,
  sku_id VARCHAR(100) NOT NULL, quantity BIGINT NOT NULL, reason VARCHAR(200), created_at DATETIME(6) NOT NULL,
  INDEX idx_tenant_warehouse (tenant_id, warehouse_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS location_permission (
  user_id VARCHAR(100) NOT NULL, tenant_id VARCHAR(100) NOT NULL, location_id VARCHAR(100) NOT NULL,
  PRIMARY KEY (tenant_id, user_id, location_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS serial_tracking (
  serial_id VARCHAR(100) NOT NULL PRIMARY KEY, tenant_id VARCHAR(100) NOT NULL, serial_number VARCHAR(100) NOT NULL,
  sku_id VARCHAR(100) NOT NULL, warehouse_id VARCHAR(100), lot_id VARCHAR(100), created_at DATETIME(6) NOT NULL,
  INDEX idx_tenant_serial (tenant_id, serial_number)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
