-- LIS 细胞独立 Schema（医疗合规：检验申请→样本→检验结果→报告生成→报告审核；样本加密、报告可追溯、修改可审计）
SET NAMES utf8mb4;
CREATE TABLE event_store (
  event_id BIGINT PRIMARY KEY AUTO_INCREMENT, aggregate_type VARCHAR(50) NOT NULL, aggregate_id VARCHAR(100) NOT NULL,
  event_type VARCHAR(100) NOT NULL, event_data JSON NOT NULL, event_version INT NOT NULL DEFAULT 1,
  occurred_on DATETIME(6) NOT NULL, recorded_by VARCHAR(100) NOT NULL, recorded_at DATETIME(6) NOT NULL,
  tenant_id VARCHAR(100) NOT NULL,
  INDEX idx_aggregate (aggregate_type, aggregate_id), INDEX idx_tenant_recorded (tenant_id, recorded_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS test_request (
  request_id VARCHAR(100) NOT NULL PRIMARY KEY, tenant_id VARCHAR(100) NOT NULL, patient_id VARCHAR(100),
  visit_id VARCHAR(100), items TEXT, status TINYINT NOT NULL DEFAULT 1, created_at DATETIME(6) NOT NULL,
  INDEX idx_tenant_created (tenant_id, created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE sample_read_model (
  sample_id VARCHAR(100) PRIMARY KEY, tenant_id VARCHAR(100) NOT NULL, sample_no VARCHAR(64), patient_id VARCHAR(100),
  request_id VARCHAR(100), specimen_type VARCHAR(64), technician_id VARCHAR(100), status TINYINT NOT NULL,
  created_at DATETIME(6) NOT NULL, updated_at DATETIME(6) NOT NULL,
  INDEX idx_tenant_order (tenant_id, request_id), INDEX idx_tenant_technician (tenant_id, technician_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE result_read_model (
  result_id VARCHAR(100) PRIMARY KEY, tenant_id VARCHAR(100) NOT NULL, sample_id VARCHAR(100),
  item_code VARCHAR(64), value_encrypted TEXT, unit VARCHAR(32), status TINYINT NOT NULL,
  created_at DATETIME(6) NOT NULL, updated_at DATETIME(6) NOT NULL,
  INDEX idx_tenant_sample (tenant_id, sample_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS lab_report (
  report_id VARCHAR(100) NOT NULL PRIMARY KEY, tenant_id VARCHAR(100) NOT NULL, sample_id VARCHAR(100) NOT NULL,
  request_id VARCHAR(100), content TEXT, status TINYINT NOT NULL DEFAULT 0 COMMENT '0草稿 1已审核',
  created_at DATETIME(6) NOT NULL, reviewed_at DATETIME(6), reviewed_by VARCHAR(100),
  INDEX idx_tenant_sample (tenant_id, sample_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS report_audit_log (
  audit_id VARCHAR(100) NOT NULL PRIMARY KEY, tenant_id VARCHAR(100) NOT NULL, report_id VARCHAR(100) NOT NULL,
  operation VARCHAR(50) NOT NULL, operator_id VARCHAR(100), occurred_at DATETIME(6) NOT NULL,
  INDEX idx_report (report_id), INDEX idx_tenant_time (tenant_id, occurred_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE audit_log (
  log_id BIGINT PRIMARY KEY AUTO_INCREMENT, tenant_id VARCHAR(100) NOT NULL, user_id VARCHAR(100) NOT NULL,
  operation_type VARCHAR(50) NOT NULL, operation_result TINYINT NOT NULL, trace_id VARCHAR(64), occurred_at DATETIME(6) NOT NULL,
  INDEX idx_tenant_user_time (tenant_id, user_id, occurred_at), INDEX idx_trace_id (trace_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
