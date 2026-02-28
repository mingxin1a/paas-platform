-- HRM 细胞独立 Schema，多租户、utf8mb4
SET NAMES utf8mb4;
CREATE TABLE event_store (
  event_id BIGINT PRIMARY KEY AUTO_INCREMENT, aggregate_type VARCHAR(50) NOT NULL, aggregate_id VARCHAR(100) NOT NULL,
  event_type VARCHAR(100) NOT NULL, event_data JSON NOT NULL, tenant_id VARCHAR(100) NOT NULL,
  occurred_on DATETIME(6) NOT NULL, recorded_at DATETIME(6) NOT NULL,
  INDEX idx_aggregate (aggregate_type, aggregate_id), INDEX idx_tenant_recorded (tenant_id, recorded_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
CREATE TABLE employee_read_model (
  employee_id VARCHAR(100) PRIMARY KEY, tenant_id VARCHAR(100) NOT NULL, department_id VARCHAR(100),
  name VARCHAR(200) NOT NULL, employee_no VARCHAR(64), status TINYINT NOT NULL DEFAULT 1,
  created_at DATETIME(6) NOT NULL, updated_at DATETIME(6) NOT NULL,
  INDEX idx_tenant_department (tenant_id, department_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
CREATE TABLE department_read_model (
  department_id VARCHAR(100) PRIMARY KEY, tenant_id VARCHAR(100) NOT NULL, name VARCHAR(200) NOT NULL,
  parent_id VARCHAR(100), created_at DATETIME(6) NOT NULL,
  INDEX idx_tenant (tenant_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
CREATE TABLE leave_request_read_model (
  request_id VARCHAR(100) PRIMARY KEY, tenant_id VARCHAR(100) NOT NULL, employee_id VARCHAR(100) NOT NULL,
  leave_type VARCHAR(50), start_date DATE, end_date DATE, days DECIMAL(5,2), status TINYINT NOT NULL DEFAULT 1,
  created_at DATETIME(6) NOT NULL,
  INDEX idx_tenant_employee (tenant_id, employee_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
CREATE TABLE audit_log (
  log_id BIGINT PRIMARY KEY AUTO_INCREMENT, tenant_id VARCHAR(100) NOT NULL, user_id VARCHAR(100) NOT NULL,
  operation_type VARCHAR(50) NOT NULL, operation_result TINYINT NOT NULL, trace_id VARCHAR(64), occurred_at DATETIME(6) NOT NULL,
  INDEX idx_tenant_user_time (tenant_id, user_id, occurred_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
