-- Config storage table for runtime config management with multi-tenancy

CREATE TABLE IF NOT EXISTS optorch_config (
    namespace VARCHAR(255) NOT NULL,
    organization_id VARCHAR(255) DEFAULT NULL,
    config_data JSON NOT NULL,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE,
    PRIMARY KEY (namespace, organization_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Indexes
CREATE INDEX idx_optorch_config_updated ON optorch_config(updated_at DESC);
CREATE INDEX idx_optorch_config_active ON optorch_config(is_active);
CREATE INDEX idx_optorch_config_org ON optorch_config(organization_id);
