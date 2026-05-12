-- Config storage table for runtime config management with multi-tenancy

CREATE TABLE IF NOT EXISTS optorch_config (
    namespace TEXT NOT NULL,
    organization_id TEXT DEFAULT NULL,
    config_data JSONB NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    is_active BOOLEAN DEFAULT TRUE,
    PRIMARY KEY (namespace, organization_id)
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_optorch_config_updated ON optorch_config(updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_optorch_config_active ON optorch_config(is_active) WHERE is_active = TRUE;
CREATE INDEX IF NOT EXISTS idx_optorch_config_namespace_prefix ON optorch_config(namespace text_pattern_ops);
CREATE INDEX IF NOT EXISTS idx_optorch_config_org ON optorch_config(organization_id);
