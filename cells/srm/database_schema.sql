-- SRM 细胞独立 Schema（商用级：供应商准入、评估、询报价、对账、评级）
SET NAMES utf8mb4;
CREATE TABLE event_store (
  event_id BIGINT PRIMARY KEY AUTO_INCREMENT, aggregate_type VARCHAR(50) NOT NULL, aggregate_id VARCHAR(100) NOT NULL,
  event_type VARCHAR(100) NOT NULL, event_data JSON NOT NULL, event_version INT NOT NULL DEFAULT 1,
  occurred_on DATETIME(6) NOT NULL, recorded_by VARCHAR(100) NOT NULL, recorded_at DATETIME(6) NOT NULL,
  tenant_id VARCHAR(100) NOT NULL,
  INDEX idx_aggregate (aggregate_type, aggregate_id), INDEX idx_tenant_recorded (tenant_id, recorded_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
CREATE TABLE supplier_read_model (
  supplier_id VARCHAR(100) PRIMARY KEY, tenant_id VARCHAR(100) NOT NULL, name VARCHAR(200), status TINYINT NOT NULL,
  created_at DATETIME(6) NOT NULL, updated_at DATETIME(6) NOT NULL, INDEX idx_tenant_status (tenant_id, status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
CREATE TABLE purchase_order_read_model (
  order_id VARCHAR(100) PRIMARY KEY, tenant_id VARCHAR(100) NOT NULL, supplier_id VARCHAR(100), total_cents BIGINT, status TINYINT NOT NULL,
  created_at DATETIME(6) NOT NULL, updated_at DATETIME(6) NOT NULL, INDEX idx_tenant_status (tenant_id, status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
CREATE TABLE audit_log (
  log_id BIGINT PRIMARY KEY AUTO_INCREMENT, tenant_id VARCHAR(100) NOT NULL, user_id VARCHAR(100) NOT NULL,
  operation_type VARCHAR(50) NOT NULL, operation_result TINYINT NOT NULL, trace_id VARCHAR(64), occurred_at DATETIME(6) NOT NULL,
  INDEX idx_tenant_user_time (tenant_id, user_id, occurred_at), INDEX idx_trace_id (trace_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 供应商准入审核
CREATE TABLE IF NOT EXISTS supplier_onboarding (
  onboarding_id VARCHAR(100) NOT NULL PRIMARY KEY, tenant_id VARCHAR(100) NOT NULL, supplier_id VARCHAR(100) NOT NULL,
  status VARCHAR(20) NOT NULL DEFAULT 'pending' COMMENT 'pending|approved|rejected',
  approved_by VARCHAR(100), approved_at DATETIME(6), created_at DATETIME(6) NOT NULL,
  INDEX idx_tenant_status (tenant_id, status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 供应商评估
CREATE TABLE IF NOT EXISTS supplier_evaluation (
  evaluation_id VARCHAR(100) NOT NULL PRIMARY KEY, tenant_id VARCHAR(100) NOT NULL, supplier_id VARCHAR(100) NOT NULL,
  score INT, dimension VARCHAR(100), comment TEXT, evaluated_at DATETIME(6) NOT NULL, created_at DATETIME(6) NOT NULL,
  INDEX idx_tenant_supplier (tenant_id, supplier_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 采购需求（采购专员数据权限：仅看自己负责的供应商）
CREATE TABLE IF NOT EXISTS purchase_demand (
  demand_id VARCHAR(100) NOT NULL PRIMARY KEY, tenant_id VARCHAR(100) NOT NULL, owner_id VARCHAR(100) NOT NULL,
  supplier_id VARCHAR(100), material_desc VARCHAR(500), quantity DECIMAL(18,6), created_at DATETIME(6) NOT NULL,
  INDEX idx_tenant_owner (tenant_id, owner_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 询价单 RFQ
CREATE TABLE IF NOT EXISTS rfq (
  rfq_id VARCHAR(100) NOT NULL PRIMARY KEY, tenant_id VARCHAR(100) NOT NULL, demand_id VARCHAR(100),
  status VARCHAR(20) NOT NULL DEFAULT 'open', created_at DATETIME(6) NOT NULL,
  INDEX idx_tenant_status (tenant_id, status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 供应商报价（商用：报价可加密存储）
CREATE TABLE IF NOT EXISTS supplier_quote (
  quote_id VARCHAR(100) NOT NULL PRIMARY KEY, tenant_id VARCHAR(100) NOT NULL, rfq_id VARCHAR(100) NOT NULL,
  supplier_id VARCHAR(100) NOT NULL, amount_cents BIGINT NOT NULL, currency VARCHAR(10) DEFAULT 'CNY',
  valid_until DATE, created_at DATETIME(6) NOT NULL,
  INDEX idx_rfq (rfq_id), INDEX idx_tenant_supplier (tenant_id, supplier_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 供应商对账
CREATE TABLE IF NOT EXISTS supplier_reconciliation (
  reconciliation_id VARCHAR(100) NOT NULL PRIMARY KEY, tenant_id VARCHAR(100) NOT NULL, supplier_id VARCHAR(100) NOT NULL,
  period_start DATE, period_end DATE, amount_cents BIGINT, status VARCHAR(20), created_at DATETIME(6) NOT NULL,
  INDEX idx_tenant_supplier (tenant_id, supplier_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 供应商评级
CREATE TABLE IF NOT EXISTS supplier_rating (
  rating_id VARCHAR(100) NOT NULL PRIMARY KEY, tenant_id VARCHAR(100) NOT NULL, supplier_id VARCHAR(100) NOT NULL,
  level VARCHAR(20), score INT, valid_from DATE, created_at DATETIME(6) NOT NULL,
  INDEX idx_tenant_supplier (tenant_id, supplier_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
