-- HIS 细胞独立 Schema（医疗合规：患者→挂号→就诊→处方→收费→住院→病历；患者信息加密+脱敏，病历不可篡改）
SET NAMES utf8mb4;
CREATE TABLE event_store (
  event_id BIGINT PRIMARY KEY AUTO_INCREMENT, aggregate_type VARCHAR(50) NOT NULL, aggregate_id VARCHAR(100) NOT NULL,
  event_type VARCHAR(100) NOT NULL, event_data JSON NOT NULL, event_version INT NOT NULL DEFAULT 1,
  occurred_on DATETIME(6) NOT NULL, recorded_by VARCHAR(100) NOT NULL, recorded_at DATETIME(6) NOT NULL,
  tenant_id VARCHAR(100) NOT NULL,
  INDEX idx_aggregate (aggregate_type, aggregate_id), INDEX idx_tenant_recorded (tenant_id, recorded_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE patient_read_model (
  patient_id VARCHAR(100) PRIMARY KEY, tenant_id VARCHAR(100) NOT NULL, patient_no VARCHAR(64),
  name_encrypted VARCHAR(500), id_no_encrypted VARCHAR(500), gender VARCHAR(20),
  doctor_id VARCHAR(100), status TINYINT NOT NULL,
  created_at DATETIME(6) NOT NULL, updated_at DATETIME(6) NOT NULL,
  INDEX idx_tenant_status (tenant_id, status), INDEX idx_tenant_doctor (tenant_id, doctor_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE visit_read_model (
  visit_id VARCHAR(100) PRIMARY KEY, tenant_id VARCHAR(100) NOT NULL, patient_id VARCHAR(100),
  department_id VARCHAR(100), doctor_id VARCHAR(100), status TINYINT NOT NULL,
  created_at DATETIME(6) NOT NULL, updated_at DATETIME(6) NOT NULL,
  INDEX idx_tenant_patient (tenant_id, patient_id), INDEX idx_tenant_doctor (tenant_id, doctor_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS registration (
  registration_id VARCHAR(100) NOT NULL PRIMARY KEY, tenant_id VARCHAR(100) NOT NULL,
  patient_id VARCHAR(100) NOT NULL, department_id VARCHAR(100), schedule_date DATE,
  status TINYINT NOT NULL DEFAULT 1, created_at DATETIME(6) NOT NULL,
  idempotent_key VARCHAR(128) UNIQUE,
  INDEX idx_tenant_patient (tenant_id, patient_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS prescription (
  prescription_id VARCHAR(100) NOT NULL PRIMARY KEY, tenant_id VARCHAR(100) NOT NULL, visit_id VARCHAR(100) NOT NULL,
  content_hash VARCHAR(64), drug_list TEXT, status TINYINT NOT NULL DEFAULT 1, created_at DATETIME(6) NOT NULL,
  INDEX idx_visit (visit_id), UNIQUE KEY uk_visit_content (visit_id, content_hash)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS charge (
  charge_id VARCHAR(100) NOT NULL PRIMARY KEY, tenant_id VARCHAR(100) NOT NULL, visit_id VARCHAR(100) NOT NULL,
  amount_cents BIGINT NOT NULL, paid_cents BIGINT NOT NULL DEFAULT 0, status TINYINT NOT NULL DEFAULT 1,
  created_at DATETIME(6) NOT NULL, idempotent_key VARCHAR(128) UNIQUE,
  INDEX idx_tenant_visit (tenant_id, visit_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS inpatient (
  inpatient_id VARCHAR(100) NOT NULL PRIMARY KEY, tenant_id VARCHAR(100) NOT NULL, patient_id VARCHAR(100) NOT NULL,
  bed_no VARCHAR(32), admitted_at DATETIME(6), status TINYINT NOT NULL DEFAULT 1, created_at DATETIME(6) NOT NULL,
  INDEX idx_tenant_patient (tenant_id, patient_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS medical_record (
  record_id VARCHAR(100) NOT NULL PRIMARY KEY, tenant_id VARCHAR(100) NOT NULL, patient_id VARCHAR(100) NOT NULL,
  visit_id VARCHAR(100), content_immutable TEXT COMMENT '病历内容不可篡改，追加 only',
  created_at DATETIME(6) NOT NULL,
  INDEX idx_tenant_patient (tenant_id, patient_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE audit_log (
  log_id BIGINT PRIMARY KEY AUTO_INCREMENT, tenant_id VARCHAR(100) NOT NULL, user_id VARCHAR(100) NOT NULL,
  operation_type VARCHAR(50) NOT NULL, operation_result TINYINT NOT NULL, trace_id VARCHAR(64), occurred_at DATETIME(6) NOT NULL,
  INDEX idx_tenant_user_time (tenant_id, user_id, occurred_at), INDEX idx_trace_id (trace_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
