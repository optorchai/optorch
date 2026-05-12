-- Migration: Add Casbin policy storage table
CREATE TABLE IF NOT EXISTS casbin_policies (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ptype TEXT NOT NULL,
    rule TEXT NOT NULL,  -- JSON array
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_casbin_ptype ON casbin_policies(ptype);
CREATE INDEX IF NOT EXISTS idx_casbin_ptype_rule ON casbin_policies(ptype, rule);
