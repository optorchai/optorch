-- Casbin policies storage
CREATE TABLE IF NOT EXISTS casbin_policies (
    id INT AUTO_INCREMENT PRIMARY KEY,
    ptype VARCHAR(10) NOT NULL,
    rule JSON NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_casbin_ptype (ptype),
    INDEX idx_casbin_ptype_rule (ptype, rule(255))
);
