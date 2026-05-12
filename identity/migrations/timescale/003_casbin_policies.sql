-- Casbin policies storage
CREATE TABLE IF NOT EXISTS casbin_policies (
    id SERIAL PRIMARY KEY,
    ptype VARCHAR(10) NOT NULL,
    rule JSONB NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_casbin_ptype ON casbin_policies(ptype);
CREATE INDEX IF NOT EXISTS idx_casbin_ptype_rule ON casbin_policies(ptype, rule);
