-- Identity system tables (TimescaleDB/PostgreSQL) - TMF632 Party Management + Auth

-- Organizations (TMF632)
CREATE TABLE IF NOT EXISTS organizations (
    id BIGSERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    href VARCHAR(512),
    organization_type VARCHAR(50) NOT NULL DEFAULT 'Company',
    status VARCHAR(50) NOT NULL DEFAULT 'active',
    parent_id BIGINT,
    license JSONB,
    contact JSONB,  -- array of ContactMedium
    characteristic JSONB,  -- array of OrganizationCharacteristic
    metadata JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    FOREIGN KEY (parent_id) REFERENCES organizations(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_organizations_parent ON organizations(parent_id);
CREATE INDEX IF NOT EXISTS idx_organizations_created ON organizations(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_organizations_license ON organizations USING GIN (license);

-- Individuals (TMF632)
CREATE TABLE IF NOT EXISTS individuals (
    id VARCHAR(255) PRIMARY KEY,
    given_name VARCHAR(255),
    family_name VARCHAR(255),
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255),
    status VARCHAR(50) NOT NULL DEFAULT 'active',
    metadata JSONB,
    last_login_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_individuals_email ON individuals(email);
CREATE INDEX IF NOT EXISTS idx_individuals_status ON individuals(status) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_individuals_last_login ON individuals(last_login_at DESC);
CREATE INDEX IF NOT EXISTS idx_individuals_metadata ON individuals USING GIN (metadata);

-- Organization Memberships (TMF632)
CREATE TABLE IF NOT EXISTS organization_memberships (
    id VARCHAR(255) PRIMARY KEY,
    individual_id VARCHAR(255) NOT NULL,
    organization_id BIGINT NOT NULL,
    roles JSONB NOT NULL DEFAULT '[]'::jsonb,
    status VARCHAR(50) NOT NULL DEFAULT 'active',
    joined_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    FOREIGN KEY (individual_id) REFERENCES individuals(id) ON DELETE CASCADE,
    FOREIGN KEY (organization_id) REFERENCES organizations(id) ON DELETE CASCADE,
    UNIQUE (individual_id, organization_id)
);

CREATE INDEX IF NOT EXISTS idx_memberships_individual ON organization_memberships(individual_id);
CREATE INDEX IF NOT EXISTS idx_memberships_organization ON organization_memberships(organization_id);
CREATE INDEX IF NOT EXISTS idx_memberships_status ON organization_memberships(status);
CREATE INDEX IF NOT EXISTS idx_memberships_roles ON organization_memberships USING GIN (roles);

-- SCIM Tokens (per-tenant provisioning)
CREATE TABLE IF NOT EXISTS scim_tokens (
    id VARCHAR(255) PRIMARY KEY,
    organization_id VARCHAR(255) NOT NULL,
    token_hash VARCHAR(255) NOT NULL UNIQUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMPTZ,
    last_used_at TIMESTAMPTZ,
    FOREIGN KEY (organization_id) REFERENCES organizations(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_scim_tokens_org ON scim_tokens(organization_id);
CREATE INDEX IF NOT EXISTS idx_scim_tokens_hash ON scim_tokens(token_hash);
CREATE INDEX IF NOT EXISTS idx_scim_tokens_expires ON scim_tokens(expires_at);

-- Authorization Policies (Casbin storage - optional, config-based is preferred)
CREATE TABLE IF NOT EXISTS authorization_policies (
    id VARCHAR(255) PRIMARY KEY,
    ptype VARCHAR(50) NOT NULL,
    v0 VARCHAR(255),
    v1 VARCHAR(255),
    v2 VARCHAR(255),
    v3 VARCHAR(255),
    v4 VARCHAR(255),
    v5 VARCHAR(255),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_policies_ptype ON authorization_policies(ptype);
CREATE INDEX IF NOT EXISTS idx_policies_v0 ON authorization_policies(v0);
CREATE INDEX IF NOT EXISTS idx_policies_v1 ON authorization_policies(v1);
CREATE INDEX IF NOT EXISTS idx_policies_v0_v1 ON authorization_policies(v0, v1);

-- Update triggers for updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_organizations_updated_at BEFORE UPDATE ON organizations
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_individuals_updated_at BEFORE UPDATE ON individuals
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_memberships_updated_at BEFORE UPDATE ON organization_memberships
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
