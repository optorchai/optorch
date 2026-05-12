-- Identity system tables (MySQL) - TMF632 Party Management + Auth

-- Organizations (TMF632)
CREATE TABLE IF NOT EXISTS organizations (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(255) NOT NULL,
    href VARCHAR(512),
    organization_type VARCHAR(50) NOT NULL DEFAULT 'Company',
    status VARCHAR(50) NOT NULL DEFAULT 'active',
    parent_id BIGINT,
    license JSON,
    contact JSON,  -- array of ContactMedium
    characteristic JSON,  -- array of OrganizationCharacteristic
    metadata JSON,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (parent_id) REFERENCES organizations(id) ON DELETE CASCADE,
    INDEX idx_organizations_parent (parent_id),
    INDEX idx_organizations_created (created_at DESC),
    INDEX idx_organizations_type (organization_type),
    INDEX idx_organizations_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Individuals (TMF632)
CREATE TABLE IF NOT EXISTS individuals (
    id VARCHAR(255) PRIMARY KEY,
    given_name VARCHAR(255),
    family_name VARCHAR(255),
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255),
    status VARCHAR(50) NOT NULL DEFAULT 'active',
    metadata JSON,
    last_login_at TIMESTAMP NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    deleted_at TIMESTAMP NULL,
    INDEX idx_individuals_email (email),
    INDEX idx_individuals_status (status, deleted_at),
    INDEX idx_individuals_last_login (last_login_at DESC)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Organization Memberships (TMF632)
CREATE TABLE IF NOT EXISTS organization_memberships (
    id VARCHAR(255) PRIMARY KEY,
    individual_id VARCHAR(255) NOT NULL,
    organization_id BIGINT NOT NULL,
    roles JSON NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'active',
    joined_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (individual_id) REFERENCES individuals(id) ON DELETE CASCADE,
    FOREIGN KEY (organization_id) REFERENCES organizations(id) ON DELETE CASCADE,
    UNIQUE KEY unique_membership (individual_id, organization_id),
    INDEX idx_memberships_individual (individual_id),
    INDEX idx_memberships_organization (organization_id),
    INDEX idx_memberships_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- SCIM Tokens (per-tenant provisioning)
CREATE TABLE IF NOT EXISTS scim_tokens (
    id VARCHAR(255) PRIMARY KEY,
    organization_id VARCHAR(255) NOT NULL,
    token_hash VARCHAR(255) NOT NULL UNIQUE,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP NULL,
    last_used_at TIMESTAMP NULL,
    FOREIGN KEY (organization_id) REFERENCES organizations(id) ON DELETE CASCADE,
    INDEX idx_scim_tokens_org (organization_id),
    INDEX idx_scim_tokens_hash (token_hash),
    INDEX idx_scim_tokens_expires (expires_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

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
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_policies_ptype (ptype),
    INDEX idx_policies_v0 (v0),
    INDEX idx_policies_v1 (v1),
    INDEX idx_policies_v0_v1 (v0, v1)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
