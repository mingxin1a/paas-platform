-- LIMS 细胞独立 Schema（行业合规：样品→实验任务→实验数据→实验报告→数据溯源；实验数据留存≥5年）
SET NAMES utf8mb4;
CREATE TABLE event_store (
  event_id BIGINT PRIMARY KEY AUTO_INCREMENT, aggregate_type VARCHAR(50) NOT NULL, aggregate_id VARCHAR(100) NOT NULL,
  event_type VARCHAR(100) NOT NULL, event_data JSON NOT NULL, event_version INT NOT NULL DEFAULT 1,
  occurred_on DATETIME(6) NOT NULL, recorded_by VARCHAR(100) NOT NULL, recorded_at DATETIME(6) NOT NULL,
  tenant_id VARCHAR(100) NOT NULL,
  INDEX idx_aggregate (aggregate_type, aggregate_id), INDEX idx_tenant_recorded (tenant_id, recorded_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE sample_read_model (
  sample_id VARCHAR(100) PRIMARY KEY, tenant_id VARCHAR(100) NOT NULL, sample_no VARCHAR(64), batch_id VARCHAR(100),
  test_type VARCHAR(64), operator_id VARCHAR(100), status TINYINT NOT NULL,
  created_at DATETIME(6) NOT NULL, updated_at DATETIME(6) NOT NULL,
  INDEX idx_tenant_status (tenant_id, status), INDEX idx_tenant_operator (tenant_id, operator_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS experiment_task (
  task_id VARCHAR(100) NOT NULL PRIMARY KEY, tenant_id VARCHAR(100) NOT NULL, sample_id VARCHAR(100) NOT NULL,
  task_type VARCHAR(64), status TINYINT NOT NULL DEFAULT 0, operator_id VARCHAR(100),
  created_at DATETIME(6) NOT NULL, completed_at DATETIME(6),
  INDEX idx_tenant_sample (tenant_id, sample_id), INDEX idx_tenant_operator (tenant_id, operator_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS experiment_data (
  data_id VARCHAR(100) NOT NULL PRIMARY KEY, tenant_id VARCHAR(100) NOT NULL, task_id VARCHAR(100) NOT NULL,
  sample_id VARCHAR(100) NOT NULL, data_encrypted TEXT, created_at DATETIME(6) NOT NULL,
  INDEX idx_tenant_task (tenant_id, task_id), INDEX idx_tenant_sample (tenant_id, sample_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS experiment_report (
  report_id VARCHAR(100) NOT NULL PRIMARY KEY, tenant_id VARCHAR(100) NOT NULL, sample_id VARCHAR(100) NOT NULL,
  task_id VARCHAR(100), content TEXT, created_at DATETIME(6) NOT NULL,
  INDEX idx_tenant_sample (tenant_id, sample_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS data_trace (
  trace_id VARCHAR(100) NOT NULL PRIMARY KEY, tenant_id VARCHAR(100) NOT NULL,
  entity_type VARCHAR(50) NOT NULL, entity_id VARCHAR(100) NOT NULL, action VARCHAR(50), operator_id VARCHAR(100),
  occurred_at DATETIME(6) NOT NULL,
  INDEX idx_tenant_entity (tenant_id, entity_type, entity_id), INDEX idx_tenant_time (tenant_id, occurred_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT '数据溯源可审计';

CREATE TABLE result_read_model (
  result_id VARCHAR(100) PRIMARY KEY, tenant_id VARCHAR(100) NOT NULL, sample_id VARCHAR(100),
  test_item VARCHAR(64), value_encrypted TEXT, unit VARCHAR(32), created_at DATETIME(6) NOT NULL,
  INDEX idx_tenant_sample (tenant_id, sample_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE audit_log (
  log_id BIGINT PRIMARY KEY AUTO_INCREMENT, tenant_id VARCHAR(100) NOT NULL, user_id VARCHAR(100) NOT NULL,
  operation_type VARCHAR(50) NOT NULL, operation_result TINYINT NOT NULL, trace_id VARCHAR(64), occurred_at DATETIME(6) NOT NULL,
  INDEX idx_tenant_user_time (tenant_id, user_id, occurred_at), INDEX idx_trace_id (trace_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
