-- Audit logs for authentication and authorization events

CREATE TABLE IF NOT EXISTS audit_logs (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    subject VARCHAR(255) NOT NULL,
    resource VARCHAR(255) NOT NULL,
    action VARCHAR(255) NOT NULL,
    decision VARCHAR(50) NOT NULL,
    provider VARCHAR(100),
    reason TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_audit_logs_subject (subject),
    INDEX idx_audit_logs_resource (resource),
    INDEX idx_audit_logs_action (action),
    INDEX idx_audit_logs_decision (decision),
    INDEX idx_audit_logs_created (created_at DESC)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
