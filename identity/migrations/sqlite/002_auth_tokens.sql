-- Auth tokens for builtin provider (SQLite)

-- Invite tokens for new user registration
CREATE TABLE IF NOT EXISTS invite_tokens (
    id TEXT PRIMARY KEY,
    token TEXT NOT NULL UNIQUE,
    individual_id TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'active',
    expiry TIMESTAMP NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT (datetime('now')),
    created_by TEXT NOT NULL,
    used_at TIMESTAMP,
    FOREIGN KEY (individual_id) REFERENCES individuals(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_invite_tokens_token ON invite_tokens(token);
CREATE INDEX IF NOT EXISTS idx_invite_tokens_individual ON invite_tokens(individual_id);
CREATE INDEX IF NOT EXISTS idx_invite_tokens_status ON invite_tokens(status);
CREATE INDEX IF NOT EXISTS idx_invite_tokens_expiry ON invite_tokens(expiry);

-- Password reset tokens
CREATE TABLE IF NOT EXISTS reset_tokens (
    id TEXT PRIMARY KEY,
    token TEXT NOT NULL UNIQUE,
    individual_id TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'active',
    expiry TIMESTAMP NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT (datetime('now')),
    used_at TIMESTAMP,
    FOREIGN KEY (individual_id) REFERENCES individuals(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_reset_tokens_token ON reset_tokens(token);
CREATE INDEX IF NOT EXISTS idx_reset_tokens_individual ON reset_tokens(individual_id);
CREATE INDEX IF NOT EXISTS idx_reset_tokens_status ON reset_tokens(status);
CREATE INDEX IF NOT EXISTS idx_reset_tokens_expiry ON reset_tokens(expiry);

-- Refresh tokens (optional, for stateful refresh token tracking)
CREATE TABLE IF NOT EXISTS refresh_tokens (
    id TEXT PRIMARY KEY,
    token_hash TEXT NOT NULL UNIQUE,
    individual_id TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'active',
    expires_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT (datetime('now')),
    revoked_at TIMESTAMP,
    last_used_at TIMESTAMP,
    FOREIGN KEY (individual_id) REFERENCES individuals(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_refresh_tokens_hash ON refresh_tokens(token_hash);
CREATE INDEX IF NOT EXISTS idx_refresh_tokens_individual ON refresh_tokens(individual_id);
CREATE INDEX IF NOT EXISTS idx_refresh_tokens_status ON refresh_tokens(status);
CREATE INDEX IF NOT EXISTS idx_refresh_tokens_expires ON refresh_tokens(expires_at);

-- Session storage for user sessions
CREATE TABLE IF NOT EXISTS user_sessions (
    id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL UNIQUE,
    individual_id TEXT NOT NULL,
    data TEXT NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT (datetime('now')),
    updated_at TIMESTAMP NOT NULL DEFAULT (datetime('now')),
    expires_at TIMESTAMP NOT NULL,
    FOREIGN KEY (individual_id) REFERENCES individuals(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_user_sessions_session_id ON user_sessions(session_id);
CREATE INDEX IF NOT EXISTS idx_user_sessions_individual ON user_sessions(individual_id);
CREATE INDEX IF NOT EXISTS idx_user_sessions_expires ON user_sessions(expires_at);

-- Update trigger for sessions
CREATE TRIGGER IF NOT EXISTS update_sessions_updated_at 
AFTER UPDATE ON user_sessions
BEGIN
    UPDATE user_sessions SET updated_at = datetime('now') WHERE id = NEW.id;
END;
