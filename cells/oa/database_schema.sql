-- OA 细胞独立 Schema（商用级：组织架构、审批、公告、日程、文件）
SET NAMES utf8mb4;
CREATE TABLE event_store (
  event_id BIGINT PRIMARY KEY AUTO_INCREMENT, aggregate_type VARCHAR(50) NOT NULL, aggregate_id VARCHAR(100) NOT NULL,
  event_type VARCHAR(100) NOT NULL, event_data JSON NOT NULL, event_version INT NOT NULL DEFAULT 1,
  occurred_on DATETIME(6) NOT NULL, recorded_by VARCHAR(100) NOT NULL, recorded_at DATETIME(6) NOT NULL,
  tenant_id VARCHAR(100) NOT NULL,
  INDEX idx_aggregate (aggregate_type, aggregate_id), INDEX idx_tenant_recorded (tenant_id, recorded_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
CREATE TABLE task_read_model (
  task_id VARCHAR(100) PRIMARY KEY, tenant_id VARCHAR(100) NOT NULL, title VARCHAR(500), status TINYINT NOT NULL,
  created_at DATETIME(6) NOT NULL, updated_at DATETIME(6) NOT NULL, INDEX idx_tenant_status (tenant_id, status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
CREATE TABLE audit_log (
  log_id BIGINT PRIMARY KEY AUTO_INCREMENT, tenant_id VARCHAR(100) NOT NULL, user_id VARCHAR(100) NOT NULL,
  operation_type VARCHAR(50) NOT NULL, operation_result TINYINT NOT NULL, trace_id VARCHAR(64), occurred_at DATETIME(6) NOT NULL,
  INDEX idx_tenant_user_time (tenant_id, user_id, occurred_at), INDEX idx_trace_id (trace_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 组织架构（部门/用户）
CREATE TABLE IF NOT EXISTS org_dept (
  dept_id VARCHAR(100) NOT NULL PRIMARY KEY, tenant_id VARCHAR(100) NOT NULL, name VARCHAR(200) NOT NULL,
  parent_id VARCHAR(100), sort_order INT DEFAULT 0, created_at DATETIME(6) NOT NULL,
  INDEX idx_tenant_parent (tenant_id, parent_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
CREATE TABLE IF NOT EXISTS org_user (
  user_id VARCHAR(100) NOT NULL PRIMARY KEY, tenant_id VARCHAR(100) NOT NULL, dept_id VARCHAR(100),
  name VARCHAR(200) NOT NULL, role VARCHAR(50), created_at DATETIME(6) NOT NULL,
  INDEX idx_tenant_dept (tenant_id, dept_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 审批流程定义与实例（采购/报销/请假）
CREATE TABLE IF NOT EXISTS approval_definition (
  def_id VARCHAR(100) NOT NULL PRIMARY KEY, tenant_id VARCHAR(100) NOT NULL, name VARCHAR(200) NOT NULL,
  type_code VARCHAR(50) NOT NULL COMMENT 'purchase|reimburse|leave',
  node_config JSON, created_at DATETIME(6) NOT NULL, INDEX idx_tenant_type (tenant_id, type_code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
CREATE TABLE IF NOT EXISTS approval_instance (
  instance_id VARCHAR(100) NOT NULL PRIMARY KEY, tenant_id VARCHAR(100) NOT NULL, def_id VARCHAR(100) NOT NULL,
  applicant_id VARCHAR(100) NOT NULL, status VARCHAR(20) NOT NULL DEFAULT 'draft' COMMENT 'draft|pending|approved|rejected',
  current_node VARCHAR(100), form_data JSON, created_at DATETIME(6) NOT NULL, updated_at DATETIME(6) NOT NULL,
  INDEX idx_tenant_applicant (tenant_id, applicant_id), INDEX idx_tenant_status (tenant_id, status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 公告通知
CREATE TABLE IF NOT EXISTS announcement (
  announcement_id VARCHAR(100) NOT NULL PRIMARY KEY, tenant_id VARCHAR(100) NOT NULL, title VARCHAR(500) NOT NULL,
  content TEXT, publisher_id VARCHAR(100), status TINYINT DEFAULT 1, created_at DATETIME(6) NOT NULL,
  INDEX idx_tenant_created (tenant_id, created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 日程管理
CREATE TABLE IF NOT EXISTS calendar_event (
  event_id VARCHAR(100) NOT NULL PRIMARY KEY, tenant_id VARCHAR(100) NOT NULL, user_id VARCHAR(100) NOT NULL,
  title VARCHAR(500) NOT NULL, start_at DATETIME(6) NOT NULL, end_at DATETIME(6), created_at DATETIME(6) NOT NULL,
  INDEX idx_tenant_user_time (tenant_id, user_id, start_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 文件管理（基础：元数据）
CREATE TABLE IF NOT EXISTS file_meta (
  file_id VARCHAR(100) NOT NULL PRIMARY KEY, tenant_id VARCHAR(100) NOT NULL, name VARCHAR(500) NOT NULL,
  storage_path VARCHAR(500), size_bytes BIGINT, mime_type VARCHAR(100), uploader_id VARCHAR(100), created_at DATETIME(6) NOT NULL,
  INDEX idx_tenant_uploader (tenant_id, uploader_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
