-- Auth tokens for builtin provider (MySQL)

-- Invite tokens for new user registration
CREATE TABLE IF NOT EXISTS invite_tokens (
    id VARCHAR(255) PRIMARY KEY,
    token VARCHAR(512) NOT NULL UNIQUE,
    individual_id VARCHAR(255) NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'active',
    expiry TIMESTAMP NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(255) NOT NULL,
    used_at TIMESTAMP NULL,
    FOREIGN KEY (individual_id) REFERENCES individuals(id) ON DELETE CASCADE,
    INDEX idx_invite_tokens_token (token),
    INDEX idx_invite_tokens_individual (individual_id),
    INDEX idx_invite_tokens_status (status),
    INDEX idx_invite_tokens_expiry (expiry)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Password reset tokens
CREATE TABLE IF NOT EXISTS reset_tokens (
    id VARCHAR(255) PRIMARY KEY,
    token VARCHAR(512) NOT NULL UNIQUE,
    individual_id VARCHAR(255) NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'active',
    expiry TIMESTAMP NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    used_at TIMESTAMP NULL,
    FOREIGN KEY (individual_id) REFERENCES individuals(id) ON DELETE CASCADE,
    INDEX idx_reset_tokens_token (token),
    INDEX idx_reset_tokens_individual (individual_id),
    INDEX idx_reset_tokens_status (status),
    INDEX idx_reset_tokens_expiry (expiry)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Refresh tokens (optional, for stateful refresh token tracking)
CREATE TABLE IF NOT EXISTS refresh_tokens (
    id VARCHAR(255) PRIMARY KEY,
    token_hash VARCHAR(512) NOT NULL UNIQUE,
    individual_id VARCHAR(255) NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'active',
    expires_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    revoked_at TIMESTAMP NULL,
    last_used_at TIMESTAMP NULL,
    FOREIGN KEY (individual_id) REFERENCES individuals(id) ON DELETE CASCADE,
    INDEX idx_refresh_tokens_hash (token_hash),
    INDEX idx_refresh_tokens_individual (individual_id),
    INDEX idx_refresh_tokens_status (status),
    INDEX idx_refresh_tokens_expires (expires_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Session storage for user sessions
CREATE TABLE IF NOT EXISTS user_sessions (
    id VARCHAR(255) PRIMARY KEY,
    session_id VARCHAR(512) NOT NULL UNIQUE,
    individual_id VARCHAR(255) NOT NULL,
    data TEXT NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    expires_at TIMESTAMP NOT NULL,
    FOREIGN KEY (individual_id) REFERENCES individuals(id) ON DELETE CASCADE,
    INDEX idx_user_sessions_session_id (session_id),
    INDEX idx_user_sessions_individual (individual_id),
    INDEX idx_user_sessions_expires (expires_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
