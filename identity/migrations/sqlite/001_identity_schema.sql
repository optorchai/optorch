-- Identity system tables (SQLite) - TMF632 Party Management + Auth

-- Organizations (TMF632)
CREATE TABLE IF NOT EXISTS organizations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    href TEXT,
    organization_type TEXT NOT NULL DEFAULT 'Company',
    status TEXT NOT NULL DEFAULT 'active',
    parent_id INTEGER,
    license TEXT,
    contact TEXT,  -- JSON array of ContactMedium
    characteristic TEXT,  -- JSON array of OrganizationCharacteristic
    metadata TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (parent_id) REFERENCES organizations(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_organizations_parent ON organizations(parent_id);
CREATE INDEX IF NOT EXISTS idx_organizations_created ON organizations(created_at DESC);

-- Individuals (TMF632)
CREATE TABLE IF NOT EXISTS individuals (
    id TEXT PRIMARY KEY,
    given_name TEXT,
    family_name TEXT,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT,
    status TEXT NOT NULL DEFAULT 'active',
    metadata TEXT,
    last_login_at TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now')),
    deleted_at TEXT
);

CREATE INDEX IF NOT EXISTS idx_individuals_email ON individuals(email);
CREATE INDEX IF NOT EXISTS idx_individuals_status ON individuals(status) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_individuals_last_login ON individuals(last_login_at DESC);

-- Organization Memberships (TMF632)
CREATE TABLE IF NOT EXISTS organization_memberships (
    id TEXT PRIMARY KEY,
    individual_id TEXT NOT NULL,
    organization_id INTEGER NOT NULL,
    roles TEXT NOT NULL DEFAULT '[]',
    status TEXT NOT NULL DEFAULT 'active',
    joined_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (individual_id) REFERENCES individuals(id) ON DELETE CASCADE,
    FOREIGN KEY (organization_id) REFERENCES organizations(id) ON DELETE CASCADE,
    UNIQUE (individual_id, organization_id)
);

CREATE INDEX IF NOT EXISTS idx_memberships_individual ON organization_memberships(individual_id);
CREATE INDEX IF NOT EXISTS idx_memberships_organization ON organization_memberships(organization_id);
CREATE INDEX IF NOT EXISTS idx_memberships_status ON organization_memberships(status);

-- SCIM Tokens (per-tenant provisioning)
CREATE TABLE IF NOT EXISTS scim_tokens (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL,
    token_hash TEXT NOT NULL UNIQUE,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    expires_at TEXT,
    last_used_at TEXT,
    FOREIGN KEY (organization_id) REFERENCES organizations(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_scim_tokens_org ON scim_tokens(organization_id);
CREATE INDEX IF NOT EXISTS idx_scim_tokens_hash ON scim_tokens(token_hash);

-- Authorization Policies (Casbin storage - optional, config-based is preferred)
CREATE TABLE IF NOT EXISTS authorization_policies (
    id TEXT PRIMARY KEY,
    ptype TEXT NOT NULL,
    v0 TEXT,
    v1 TEXT,
    v2 TEXT,
    v3 TEXT,
    v4 TEXT,
    v5 TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_policies_ptype ON authorization_policies(ptype);
CREATE INDEX IF NOT EXISTS idx_policies_v0 ON authorization_policies(v0);
CREATE INDEX IF NOT EXISTS idx_policies_v1 ON authorization_policies(v1);

-- JWT Key Rotation Storage
CREATE TABLE IF NOT EXISTS jwt_keys (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    keys_json TEXT NOT NULL,
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_jwt_keys_updated ON jwt_keys(updated_at DESC);

-- Update triggers for updated_at
CREATE TRIGGER IF NOT EXISTS update_organizations_updated_at 
AFTER UPDATE ON organizations
BEGIN
    UPDATE organizations SET updated_at = datetime('now') WHERE id = NEW.id;
END;

CREATE TRIGGER IF NOT EXISTS update_individuals_updated_at 
AFTER UPDATE ON individuals
BEGIN
    UPDATE individuals SET updated_at = datetime('now') WHERE id = NEW.id;
END;

CREATE TRIGGER IF NOT EXISTS update_memberships_updated_at 
AFTER UPDATE ON organization_memberships
BEGIN
    UPDATE organization_memberships SET updated_at = datetime('now') WHERE id = NEW.id;
END;
