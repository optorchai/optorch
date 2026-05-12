-- Config storage table for runtime config management with multi-tenancy

CREATE TABLE IF NOT EXISTS optorch_config (
    namespace TEXT NOT NULL,
    organization_id TEXT,
    config_data TEXT NOT NULL,
    updated_at TEXT NOT NULL DEFAULT (datetime('now')),
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    is_active INTEGER DEFAULT 1,
    PRIMARY KEY (namespace, organization_id)
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_optorch_config_updated ON optorch_config(updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_optorch_config_active ON optorch_config(is_active) WHERE is_active = 1;
CREATE INDEX IF NOT EXISTS idx_optorch_config_org ON optorch_config(organization_id);
