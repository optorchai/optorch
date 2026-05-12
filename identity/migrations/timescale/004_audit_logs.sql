-- Audit logs for authentication and authorization events

CREATE TABLE IF NOT EXISTS audit_logs (
    id BIGSERIAL PRIMARY KEY,
    subject TEXT NOT NULL,
    resource TEXT NOT NULL,
    action TEXT NOT NULL,
    decision TEXT NOT NULL,
    provider TEXT,
    reason TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_audit_logs_subject ON audit_logs(subject);
CREATE INDEX IF NOT EXISTS idx_audit_logs_resource ON audit_logs(resource);
CREATE INDEX IF NOT EXISTS idx_audit_logs_action ON audit_logs(action);
CREATE INDEX IF NOT EXISTS idx_audit_logs_decision ON audit_logs(decision);
CREATE INDEX IF NOT EXISTS idx_audit_logs_created ON audit_logs(created_at DESC);

-- convert to hypertable for time-series optimization
SELECT create_hypertable('audit_logs', 'created_at', if_not_exists => TRUE);
