-- CRM 细胞独立数据库 Schema
-- 遵循《数据库设计说明书_V2.0》：细胞隔离、事件溯源、多租户、命名规范、utf8mb4
-- 分库分表：按 tenant_id 逻辑隔离；大表可按 tenant_id + 时间/ID 分表
-- 01_核心法律 2.2 / 00 修正案#4：敏感字段须 AES-256 或国密 SM4 加密存储，密钥由 KMS 管理；界面与日志严禁明文完整展示，须动态脱敏。详见《docs/敏感数据加密与脱敏规范.md》。本表 contact_phone/contact_email 为结构示例，实施时须按该规范加密或脱敏存储。

SET NAMES utf8mb4;
SET CHARACTER SET utf8mb4;

-- ----------------------------
-- 事件存储（核心变更仅追加，禁止 UPDATE）
-- ----------------------------
CREATE TABLE event_store (
  event_id BIGINT PRIMARY KEY AUTO_INCREMENT,
  aggregate_type VARCHAR(50) NOT NULL COMMENT '聚合根类型',
  aggregate_id VARCHAR(100) NOT NULL COMMENT '聚合根ID',
  event_type VARCHAR(100) NOT NULL COMMENT '事件类型',
  event_data JSON NOT NULL COMMENT '事件数据',
  event_version INT NOT NULL DEFAULT 1 COMMENT '事件版本',
  occurred_on DATETIME(6) NOT NULL COMMENT '发生时间',
  recorded_by VARCHAR(100) NOT NULL COMMENT '记录者',
  recorded_at DATETIME(6) NOT NULL COMMENT '记录时间',
  tenant_id VARCHAR(100) NOT NULL COMMENT '租户ID',
  INDEX idx_aggregate (aggregate_type, aggregate_id),
  INDEX idx_type_time (event_type, occurred_on),
  INDEX idx_tenant_recorded (tenant_id, recorded_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ----------------------------
-- 读模型：客户
-- ----------------------------
CREATE TABLE customer_read_model (
  customer_id VARCHAR(100) NOT NULL,
  tenant_id VARCHAR(100) NOT NULL,
  name VARCHAR(200) NOT NULL,
  contact_phone VARCHAR(50),
  contact_email VARCHAR(200),
  status TINYINT NOT NULL DEFAULT 1 COMMENT '1-正常 2-禁用',
  created_at DATETIME(6) NOT NULL,
  updated_at DATETIME(6) NOT NULL,
  PRIMARY KEY (customer_id),
  UNIQUE KEY uk_tenant_customer (tenant_id, customer_id),
  INDEX idx_tenant_status (tenant_id, status),
  INDEX idx_tenant_updated (tenant_id, updated_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ----------------------------
-- 读模型：商机
-- ----------------------------
CREATE TABLE opportunity_read_model (
  opportunity_id VARCHAR(100) NOT NULL,
  tenant_id VARCHAR(100) NOT NULL,
  customer_id VARCHAR(100) NOT NULL,
  title VARCHAR(500),
  amount_cents BIGINT COMMENT '金额-分',
  currency VARCHAR(10) NOT NULL DEFAULT 'CNY',
  stage TINYINT NOT NULL COMMENT '阶段',
  status TINYINT NOT NULL DEFAULT 1 COMMENT '1-进行中 2-赢单 3-输单',
  created_at DATETIME(6) NOT NULL,
  updated_at DATETIME(6) NOT NULL,
  PRIMARY KEY (opportunity_id),
  INDEX idx_tenant_customer (tenant_id, customer_id),
  INDEX idx_tenant_status (tenant_id, status),
  INDEX idx_tenant_updated (tenant_id, updated_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ----------------------------
-- 读模型：联系人
-- ----------------------------
CREATE TABLE contact_read_model (
  contact_id VARCHAR(100) NOT NULL,
  tenant_id VARCHAR(100) NOT NULL,
  customer_id VARCHAR(100) NOT NULL,
  name VARCHAR(200) NOT NULL,
  phone VARCHAR(50),
  email VARCHAR(200),
  is_primary TINYINT(1) NOT NULL DEFAULT 0,
  created_at DATETIME(6) NOT NULL,
  updated_at DATETIME(6) NOT NULL,
  PRIMARY KEY (contact_id),
  INDEX idx_tenant_customer (tenant_id, customer_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ----------------------------
-- 审计日志（180 天留存）
-- ----------------------------
CREATE TABLE audit_log (
  log_id BIGINT PRIMARY KEY AUTO_INCREMENT,
  tenant_id VARCHAR(100) NOT NULL,
  user_id VARCHAR(100) NOT NULL,
  operation_type VARCHAR(50) NOT NULL,
  operation_content TEXT,
  operation_result TINYINT NOT NULL COMMENT '1-成功 2-失败',
  client_ip VARCHAR(45),
  user_agent VARCHAR(200),
  trace_id VARCHAR(64),
  occurred_at DATETIME(6) NOT NULL,
  INDEX idx_tenant_user_time (tenant_id, user_id, occurred_at),
  INDEX idx_trace_id (trace_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ----------------------------
-- 线索（Leads，Salesforce 式）
-- ----------------------------
CREATE TABLE lead_read_model (
  lead_id VARCHAR(100) NOT NULL,
  tenant_id VARCHAR(100) NOT NULL,
  name VARCHAR(200) NOT NULL,
  company VARCHAR(300),
  phone VARCHAR(50),
  email VARCHAR(200),
  source VARCHAR(100) COMMENT '来源',
  status VARCHAR(50) NOT NULL DEFAULT 'new' COMMENT 'new|qualified|unqualified|converted',
  assigned_to VARCHAR(100),
  converted_customer_id VARCHAR(100),
  converted_opportunity_id VARCHAR(100),
  created_at DATETIME(6) NOT NULL,
  updated_at DATETIME(6) NOT NULL,
  PRIMARY KEY (lead_id),
  INDEX idx_tenant_status (tenant_id, status),
  INDEX idx_tenant_assigned (tenant_id, assigned_to)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ----------------------------
-- 商机阶段与赢率配置（状态机）
-- ----------------------------
CREATE TABLE opportunity_stage_config (
  stage_code TINYINT NOT NULL,
  stage_name VARCHAR(100) NOT NULL,
  win_probability_pct TINYINT NOT NULL COMMENT '0-100',
  sort_order TINYINT NOT NULL DEFAULT 0,
  PRIMARY KEY (stage_code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ----------------------------
-- 客户/账户关系图谱（360° 视图）
-- ----------------------------
CREATE TABLE account_relationship (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  tenant_id VARCHAR(100) NOT NULL,
  from_customer_id VARCHAR(100) NOT NULL,
  to_customer_id VARCHAR(100) NOT NULL,
  relationship_type VARCHAR(50) NOT NULL COMMENT 'parent|subsidiary|partner',
  created_at DATETIME(6) NOT NULL,
  INDEX idx_tenant_from (tenant_id, from_customer_id),
  INDEX idx_tenant_to (tenant_id, to_customer_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ----------------------------
-- 活动/任务（Activities & Tasks）
-- ----------------------------
CREATE TABLE activity_read_model (
  activity_id VARCHAR(100) NOT NULL,
  tenant_id VARCHAR(100) NOT NULL,
  activity_type VARCHAR(20) NOT NULL COMMENT 'call|meeting|task|email',
  subject VARCHAR(500) NOT NULL,
  related_lead_id VARCHAR(100),
  related_opportunity_id VARCHAR(100),
  related_customer_id VARCHAR(100),
  due_at DATETIME(6),
  completed_at DATETIME(6),
  status TINYINT NOT NULL DEFAULT 1 COMMENT '1-待办 2-已完成 3-已取消',
  created_at DATETIME(6) NOT NULL,
  updated_at DATETIME(6) NOT NULL,
  PRIMARY KEY (activity_id),
  INDEX idx_tenant_type (tenant_id, activity_type),
  INDEX idx_tenant_due (tenant_id, due_at),
  INDEX idx_tenant_status (tenant_id, status),
  INDEX idx_related_opp (tenant_id, related_opportunity_id),
  INDEX idx_related_customer (tenant_id, related_customer_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ----------------------------
-- 产品目录（Products）
-- ----------------------------
CREATE TABLE product_read_model (
  product_id VARCHAR(100) NOT NULL,
  tenant_id VARCHAR(100) NOT NULL,
  product_code VARCHAR(64) NOT NULL,
  name VARCHAR(200) NOT NULL,
  unit VARCHAR(20) NOT NULL DEFAULT 'PCS',
  standard_price_cents BIGINT NOT NULL DEFAULT 0,
  created_at DATETIME(6) NOT NULL,
  PRIMARY KEY (product_id),
  UNIQUE KEY uk_tenant_code (tenant_id, product_code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ----------------------------
-- 商机行项目（Opportunity Line Items）
-- ----------------------------
CREATE TABLE opportunity_line_item (
  line_id VARCHAR(100) NOT NULL,
  tenant_id VARCHAR(100) NOT NULL,
  opportunity_id VARCHAR(100) NOT NULL,
  product_id VARCHAR(100) NOT NULL,
  quantity DECIMAL(18,6) NOT NULL,
  unit_price_cents BIGINT NOT NULL,
  total_cents BIGINT NOT NULL,
  created_at DATETIME(6) NOT NULL,
  PRIMARY KEY (line_id),
  INDEX idx_tenant_opp (tenant_id, opportunity_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ----------------------------
-- 审批请求（Approval）
-- ----------------------------
CREATE TABLE approval_request (
  request_id VARCHAR(100) NOT NULL,
  tenant_id VARCHAR(100) NOT NULL,
  opportunity_id VARCHAR(100) NOT NULL,
  request_type VARCHAR(50) NOT NULL COMMENT 'discount|large_deal',
  requested_value_cents BIGINT,
  requested_discount_pct TINYINT,
  status VARCHAR(20) NOT NULL DEFAULT 'pending' COMMENT 'pending|approved|rejected',
  requested_by VARCHAR(100) NOT NULL,
  processed_by VARCHAR(100),
  processed_at DATETIME(6),
  comment TEXT,
  created_at DATETIME(6) NOT NULL,
  PRIMARY KEY (request_id),
  INDEX idx_tenant_status (tenant_id, status),
  INDEX idx_tenant_opp (tenant_id, opportunity_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ----------------------------
-- 脱敏配置（敏感字段动态脱敏）
-- ----------------------------
CREATE TABLE data_masking_config (
  config_id BIGINT PRIMARY KEY AUTO_INCREMENT,
  table_name VARCHAR(100) NOT NULL,
  column_name VARCHAR(100) NOT NULL,
  masking_type TINYINT NOT NULL COMMENT '1-掩码 2-哈希 3-替换',
  masking_rule VARCHAR(200),
  is_enabled TINYINT NOT NULL DEFAULT 1,
  UNIQUE KEY uk_table_column (table_name, column_name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ----------------------------
-- 商用：合同、回款、客户负责人（数据权限）
-- ----------------------------
CREATE TABLE IF NOT EXISTS contracts (
  contract_id VARCHAR(100) NOT NULL PRIMARY KEY,
  tenant_id VARCHAR(100) NOT NULL,
  customer_id VARCHAR(100) NOT NULL,
  opportunity_id VARCHAR(100) NULL,
  contract_no VARCHAR(64) NOT NULL,
  amount_cents BIGINT NOT NULL DEFAULT 0,
  currency VARCHAR(10) DEFAULT 'CNY',
  status TINYINT DEFAULT 1,
  signed_at DATETIME(6) NULL,
  created_at DATETIME(6) NOT NULL,
  updated_at DATETIME(6) NOT NULL,
  INDEX idx_contracts_tenant (tenant_id),
  INDEX idx_contracts_customer (customer_id),
  UNIQUE KEY uk_tenant_contract_no (tenant_id, contract_no)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS payment_records (
  payment_id VARCHAR(100) NOT NULL PRIMARY KEY,
  tenant_id VARCHAR(100) NOT NULL,
  contract_id VARCHAR(100) NOT NULL,
  amount_cents BIGINT NOT NULL,
  payment_at VARCHAR(32) NOT NULL,
  remark TEXT,
  created_at DATETIME(6) NOT NULL,
  INDEX idx_payment_contract (contract_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS customer_owner (
  customer_id VARCHAR(100) NOT NULL,
  tenant_id VARCHAR(100) NOT NULL,
  owner_id VARCHAR(100) NOT NULL,
  created_at DATETIME(6),
  PRIMARY KEY (customer_id, tenant_id),
  INDEX idx_customer_owner_owner (tenant_id, owner_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
