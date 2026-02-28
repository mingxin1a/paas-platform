-- PLM 细胞独立 Schema（行业合规：产品设计→BOM版本→工艺→变更→文档；研发数据管理规范）
-- 产品图纸加密存储由应用层实现；变更记录可审计
SET NAMES utf8mb4;
CREATE TABLE event_store (
  event_id BIGINT PRIMARY KEY AUTO_INCREMENT, aggregate_type VARCHAR(50) NOT NULL, aggregate_id VARCHAR(100) NOT NULL,
  event_type VARCHAR(100) NOT NULL, event_data JSON NOT NULL, event_version INT NOT NULL DEFAULT 1,
  occurred_on DATETIME(6) NOT NULL, recorded_by VARCHAR(100) NOT NULL, recorded_at DATETIME(6) NOT NULL,
  tenant_id VARCHAR(100) NOT NULL,
  INDEX idx_aggregate (aggregate_type, aggregate_id), INDEX idx_tenant_recorded (tenant_id, recorded_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE product_read_model (
  product_id VARCHAR(100) PRIMARY KEY, tenant_id VARCHAR(100) NOT NULL, product_code VARCHAR(64) NOT NULL,
  name VARCHAR(500), owner_id VARCHAR(100), status TINYINT NOT NULL,
  created_at DATETIME(6) NOT NULL, updated_at DATETIME(6) NOT NULL,
  INDEX idx_tenant_status (tenant_id, status), INDEX idx_tenant_owner (tenant_id, owner_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS bom_version (
  bom_id VARCHAR(100) NOT NULL PRIMARY KEY, tenant_id VARCHAR(100) NOT NULL, product_id VARCHAR(100) NOT NULL,
  version INT NOT NULL DEFAULT 1, parent_id VARCHAR(100), quantity DECIMAL(18,6) NOT NULL DEFAULT 1,
  created_at DATETIME(6) NOT NULL,
  INDEX idx_tenant_product_version (tenant_id, product_id, version)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS process_definition (
  process_id VARCHAR(100) NOT NULL PRIMARY KEY, tenant_id VARCHAR(100) NOT NULL, product_id VARCHAR(100),
  process_code VARCHAR(64), name VARCHAR(200), created_at DATETIME(6) NOT NULL,
  INDEX idx_tenant_product (tenant_id, product_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS change_record (
  change_id VARCHAR(100) NOT NULL PRIMARY KEY, tenant_id VARCHAR(100) NOT NULL,
  entity_type VARCHAR(50) NOT NULL, entity_id VARCHAR(100) NOT NULL,
  change_type VARCHAR(50), description TEXT, changed_by VARCHAR(100), created_at DATETIME(6) NOT NULL,
  INDEX idx_tenant_entity (tenant_id, entity_type, entity_id), INDEX idx_tenant_created (tenant_id, created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS product_document (
  doc_id VARCHAR(100) NOT NULL PRIMARY KEY, tenant_id VARCHAR(100) NOT NULL, product_id VARCHAR(100) NOT NULL,
  doc_type VARCHAR(50) NOT NULL COMMENT 'drawing|process_file', version INT NOT NULL DEFAULT 1,
  storage_path_encrypted TEXT, created_at DATETIME(6) NOT NULL,
  INDEX idx_tenant_product (tenant_id, product_id), INDEX idx_tenant_type (tenant_id, doc_type)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE audit_log (
  log_id BIGINT PRIMARY KEY AUTO_INCREMENT, tenant_id VARCHAR(100) NOT NULL, user_id VARCHAR(100) NOT NULL,
  operation_type VARCHAR(50) NOT NULL, operation_result TINYINT NOT NULL, trace_id VARCHAR(64), occurred_at DATETIME(6) NOT NULL,
  INDEX idx_tenant_user_time (tenant_id, user_id, occurred_at), INDEX idx_trace_id (trace_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
