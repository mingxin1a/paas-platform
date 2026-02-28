-- ERP 细胞独立 Schema，utf8mb4，tenant_id，事件溯源+读模型
SET NAMES utf8mb4;
CREATE TABLE event_store (
  event_id BIGINT PRIMARY KEY AUTO_INCREMENT,
  aggregate_type VARCHAR(50) NOT NULL,
  aggregate_id VARCHAR(100) NOT NULL,
  event_type VARCHAR(100) NOT NULL,
  event_data JSON NOT NULL,
  event_version INT NOT NULL DEFAULT 1,
  occurred_on DATETIME(6) NOT NULL,
  recorded_by VARCHAR(100) NOT NULL,
  recorded_at DATETIME(6) NOT NULL,
  tenant_id VARCHAR(100) NOT NULL,
  INDEX idx_aggregate (aggregate_type, aggregate_id),
  INDEX idx_tenant_recorded (tenant_id, recorded_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE order_read_model (
  order_id VARCHAR(100) NOT NULL,
  tenant_id VARCHAR(100) NOT NULL,
  customer_id VARCHAR(100) NOT NULL,
  order_status TINYINT NOT NULL,
  total_amount_cents BIGINT NOT NULL,
  currency VARCHAR(10) NOT NULL DEFAULT 'CNY',
  created_at DATETIME(6) NOT NULL,
  updated_at DATETIME(6) NOT NULL,
  deleted_at DATETIME(6) NULL COMMENT '软删除时间',
  PRIMARY KEY (order_id),
  INDEX idx_tenant_status (tenant_id, order_status),
  INDEX idx_tenant_created (tenant_id, created_at),
  INDEX idx_deleted (deleted_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ----------------------------
-- 财务总账 GL（SAP 式）
-- ----------------------------
CREATE TABLE gl_account (
  account_code VARCHAR(32) NOT NULL,
  tenant_id VARCHAR(100) NOT NULL,
  name VARCHAR(200) NOT NULL,
  account_type TINYINT NOT NULL COMMENT '1-资产 2-负债 3-权益 4-收入 5-成本',
  created_at DATETIME(6) NOT NULL,
  deleted_at DATETIME(6) NULL COMMENT '软删除时间',
  PRIMARY KEY (tenant_id, account_code),
  INDEX idx_deleted (deleted_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE gl_journal_entry (
  entry_id VARCHAR(100) NOT NULL,
  tenant_id VARCHAR(100) NOT NULL,
  document_no VARCHAR(64) NOT NULL,
  posting_date DATE NOT NULL,
  total_debit_cents BIGINT NOT NULL,
  total_credit_cents BIGINT NOT NULL,
  status TINYINT NOT NULL DEFAULT 1 COMMENT '1-草稿 2-已过账',
  created_at DATETIME(6) NOT NULL,
  deleted_at DATETIME(6) NULL COMMENT '软删除时间',
  PRIMARY KEY (entry_id),
  INDEX idx_tenant_date (tenant_id, posting_date),
  INDEX idx_deleted (deleted_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE gl_journal_line (
  line_id BIGINT PRIMARY KEY AUTO_INCREMENT,
  entry_id VARCHAR(100) NOT NULL,
  tenant_id VARCHAR(100) NOT NULL,
  account_code VARCHAR(32) NOT NULL,
  debit_cents BIGINT NOT NULL DEFAULT 0,
  credit_cents BIGINT NOT NULL DEFAULT 0,
  INDEX idx_entry (entry_id),
  INDEX idx_tenant_account (tenant_id, account_code),
  CONSTRAINT fk_gl_line_entry FOREIGN KEY (entry_id) REFERENCES gl_journal_entry(entry_id),
  CONSTRAINT fk_gl_line_account FOREIGN KEY (tenant_id, account_code) REFERENCES gl_account(tenant_id, account_code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ----------------------------
-- 应收 AR / 应付 AP
-- ----------------------------
CREATE TABLE ar_invoice (
  invoice_id VARCHAR(100) NOT NULL,
  tenant_id VARCHAR(100) NOT NULL,
  customer_id VARCHAR(100) NOT NULL,
  document_no VARCHAR(64) NOT NULL,
  amount_cents BIGINT NOT NULL,
  currency VARCHAR(10) NOT NULL DEFAULT 'CNY',
  status TINYINT NOT NULL DEFAULT 1 COMMENT '1-待收 2-部分收 3-已收',
  due_date DATE,
  created_at DATETIME(6) NOT NULL,
  deleted_at DATETIME(6) NULL COMMENT '软删除时间',
  PRIMARY KEY (invoice_id),
  INDEX idx_tenant_status (tenant_id, status),
  INDEX idx_deleted (deleted_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE ap_invoice (
  invoice_id VARCHAR(100) NOT NULL,
  tenant_id VARCHAR(100) NOT NULL,
  supplier_id VARCHAR(100) NOT NULL,
  document_no VARCHAR(64) NOT NULL,
  amount_cents BIGINT NOT NULL,
  currency VARCHAR(10) NOT NULL DEFAULT 'CNY',
  status TINYINT NOT NULL DEFAULT 1 COMMENT '1-待付 2-部分付 3-已付',
  due_date DATE,
  created_at DATETIME(6) NOT NULL,
  deleted_at DATETIME(6) NULL COMMENT '软删除时间',
  PRIMARY KEY (invoice_id),
  INDEX idx_tenant_status (tenant_id, status),
  INDEX idx_deleted (deleted_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ----------------------------
-- 物料管理 MM：采购、库存（逻辑）、发票校验
-- ----------------------------
CREATE TABLE mm_material (
  material_id VARCHAR(100) NOT NULL,
  tenant_id VARCHAR(100) NOT NULL,
  material_code VARCHAR(64) NOT NULL,
  name VARCHAR(200) NOT NULL,
  unit VARCHAR(20) NOT NULL DEFAULT 'PCS',
  created_at DATETIME(6) NOT NULL,
  deleted_at DATETIME(6) NULL COMMENT '软删除时间',
  PRIMARY KEY (material_id),
  UNIQUE KEY uk_tenant_code (tenant_id, material_code),
  INDEX idx_deleted (deleted_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE mm_purchase_order (
  po_id VARCHAR(100) NOT NULL,
  tenant_id VARCHAR(100) NOT NULL,
  supplier_id VARCHAR(100) NOT NULL,
  document_no VARCHAR(64) NOT NULL,
  status TINYINT NOT NULL DEFAULT 1 COMMENT '1-草稿 2-已发 3-部分到货 4-已关闭',
  total_amount_cents BIGINT NOT NULL DEFAULT 0,
  created_at DATETIME(6) NOT NULL,
  deleted_at DATETIME(6) NULL COMMENT '软删除时间',
  PRIMARY KEY (po_id),
  INDEX idx_tenant_status (tenant_id, status),
  INDEX idx_deleted (deleted_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE mm_invoice_verification (
  verification_id VARCHAR(100) NOT NULL,
  tenant_id VARCHAR(100) NOT NULL,
  po_id VARCHAR(100) NOT NULL,
  document_no VARCHAR(64) NOT NULL,
  amount_cents BIGINT NOT NULL,
  status TINYINT NOT NULL DEFAULT 1 COMMENT '1-待校验 2-已通过 3-拒绝',
  created_at DATETIME(6) NOT NULL,
  PRIMARY KEY (verification_id),
  INDEX idx_tenant_po (tenant_id, po_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ----------------------------
-- 生产计划 PP：BOM、工单、产能
-- ----------------------------
CREATE TABLE pp_bom (
  bom_id VARCHAR(100) NOT NULL,
  tenant_id VARCHAR(100) NOT NULL,
  product_material_id VARCHAR(100) NOT NULL,
  version INT NOT NULL DEFAULT 1,
  status TINYINT NOT NULL DEFAULT 1,
  created_at DATETIME(6) NOT NULL,
  deleted_at DATETIME(6) NULL COMMENT '软删除时间',
  PRIMARY KEY (bom_id),
  INDEX idx_tenant_product (tenant_id, product_material_id),
  INDEX idx_deleted (deleted_at),
  CONSTRAINT fk_pp_bom_material FOREIGN KEY (product_material_id) REFERENCES mm_material(material_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE pp_bom_item (
  item_id BIGINT PRIMARY KEY AUTO_INCREMENT,
  bom_id VARCHAR(100) NOT NULL,
  tenant_id VARCHAR(100) NOT NULL,
  material_id VARCHAR(100) NOT NULL,
  quantity DECIMAL(18,6) NOT NULL,
  INDEX idx_bom (bom_id),
  CONSTRAINT fk_pp_bom_item_bom FOREIGN KEY (bom_id) REFERENCES pp_bom(bom_id),
  CONSTRAINT fk_pp_bom_item_material FOREIGN KEY (material_id) REFERENCES mm_material(material_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE pp_work_order (
  work_order_id VARCHAR(100) NOT NULL,
  tenant_id VARCHAR(100) NOT NULL,
  bom_id VARCHAR(100) NOT NULL,
  product_material_id VARCHAR(100) NOT NULL,
  planned_quantity DECIMAL(18,6) NOT NULL,
  status TINYINT NOT NULL DEFAULT 1 COMMENT '1-创建 2-下达 3-生产中 4-完成',
  created_at DATETIME(6) NOT NULL,
  deleted_at DATETIME(6) NULL COMMENT '软删除时间',
  PRIMARY KEY (work_order_id),
  INDEX idx_tenant_status (tenant_id, status),
  INDEX idx_deleted (deleted_at),
  CONSTRAINT fk_pp_wo_bom FOREIGN KEY (bom_id) REFERENCES pp_bom(bom_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE audit_log (
  log_id BIGINT PRIMARY KEY AUTO_INCREMENT,
  tenant_id VARCHAR(100) NOT NULL,
  user_id VARCHAR(100) NOT NULL,
  operation_type VARCHAR(50) NOT NULL,
  operation_result TINYINT NOT NULL COMMENT '1-成功 0-失败',
  trace_id VARCHAR(64),
  resource_type VARCHAR(50) DEFAULT '',
  resource_id VARCHAR(100) DEFAULT '',
  occurred_at DATETIME(6) NOT NULL,
  INDEX idx_tenant_user_time (tenant_id, user_id, occurred_at),
  INDEX idx_trace_id (trace_id),
  INDEX idx_resource (resource_type, resource_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
