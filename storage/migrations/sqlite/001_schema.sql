-- SQLite schema for OptOrch
-- Events, interactions, and node registry tables
-- Note: SQLite doesn't support hypertables or compression - using standard tables with indexes

-- ============================================================================
-- EVENTS TABLE - Time-series event storage
-- ============================================================================
CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    type TEXT NOT NULL,
    timestamp_ms INTEGER NOT NULL,
    session_id TEXT,
    request_id TEXT,
    user_id TEXT,
    application_id TEXT,
    organization_id TEXT,
    
    -- LLM-specific
    provider TEXT,
    model TEXT,
    input_tokens INTEGER,
    output_tokens INTEGER,
    duration_ms INTEGER,
    cost REAL,
    currency TEXT DEFAULT 'USD',
    
    -- Context
    node_name TEXT,
    phase TEXT,
    tool_name TEXT,
    
    -- Metadata (stored as JSON string)
    metadata TEXT,
    
    created_at TEXT DEFAULT (datetime('now'))
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_events_session ON events(session_id);
CREATE INDEX IF NOT EXISTS idx_events_user ON events(user_id);
CREATE INDEX IF NOT EXISTS idx_events_type ON events(type);
CREATE INDEX IF NOT EXISTS idx_events_timestamp ON events(timestamp_ms DESC);
CREATE INDEX IF NOT EXISTS idx_events_node ON events(node_name);
CREATE INDEX IF NOT EXISTS idx_events_currency ON events(currency);
CREATE INDEX IF NOT EXISTS idx_events_tool ON events(tool_name);
CREATE INDEX IF NOT EXISTS idx_events_org ON events(organization_id);
CREATE INDEX IF NOT EXISTS idx_events_org_session ON events(organization_id, session_id) WHERE organization_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_events_org_timestamp ON events(organization_id, timestamp_ms) WHERE organization_id IS NOT NULL;

-- ============================================================================
-- INTERACTIONS TABLE - User interactions and form submissions
-- ============================================================================
CREATE TABLE IF NOT EXISTS interactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    
    -- Multi-tenancy
    session_id TEXT NOT NULL,
    user_id TEXT,
    application_id TEXT NOT NULL,
    client_id TEXT,
    
    -- Timing
    timestamp_ms INTEGER NOT NULL,
    created_at TEXT DEFAULT (datetime('now')),
    
    -- Interaction metadata
    interaction_type TEXT,
    node_name TEXT,
    phase TEXT,
    
    -- Request/Response (stored as JSON strings)
    request TEXT NOT NULL,
    response TEXT,
    
    -- Budget tracking
    estimated_cost REAL,
    actual_cost REAL,
    budget_limit REAL,
    approved INTEGER,  -- 0/1 for boolean
    
    model TEXT,
    status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'completed', 'rejected')),
    
    metadata TEXT
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_interactions_session ON interactions(session_id);
CREATE INDEX IF NOT EXISTS idx_interactions_user ON interactions(user_id);
CREATE INDEX IF NOT EXISTS idx_interactions_application ON interactions(application_id);
CREATE INDEX IF NOT EXISTS idx_interactions_client ON interactions(client_id);
CREATE INDEX IF NOT EXISTS idx_interactions_timestamp ON interactions(timestamp_ms DESC);
CREATE INDEX IF NOT EXISTS idx_interactions_type ON interactions(interaction_type);
CREATE INDEX IF NOT EXISTS idx_interactions_status ON interactions(status);
CREATE INDEX IF NOT EXISTS idx_interactions_app_user ON interactions(application_id, user_id);
CREATE INDEX IF NOT EXISTS idx_interactions_client_session ON interactions(client_id, session_id);

-- ============================================================================
-- INTERACTION_ENTITIES TABLE - Session entity storage
-- ============================================================================
CREATE TABLE IF NOT EXISTS interaction_entities (
    session_id TEXT NOT NULL,
    entity_type TEXT NOT NULL,
    entity_data TEXT NOT NULL,  -- JSON string
    timestamp_ms INTEGER NOT NULL,
    created_at TEXT DEFAULT (datetime('now')),
    PRIMARY KEY (session_id, entity_type)
);

CREATE INDEX IF NOT EXISTS idx_interaction_entities_timestamp ON interaction_entities(timestamp_ms DESC);
CREATE INDEX IF NOT EXISTS idx_interaction_entities_type ON interaction_entities(entity_type);

-- ============================================================================
-- NODE_REGISTRY TABLE - Static node configuration
-- ============================================================================
CREATE TABLE IF NOT EXISTS node_registry (
    node_name TEXT PRIMARY KEY,
    phase TEXT,
    domain TEXT,
    entity_type TEXT,
    class_name TEXT NOT NULL,
    
    -- Routing
    default_route TEXT,
    route_conditions TEXT,  -- JSON string
    
    -- Capabilities
    tools TEXT,  -- JSON string
    llm_model TEXT,
    streaming INTEGER DEFAULT 0,  -- 0/1 for boolean
    
    -- Metadata
    prompts TEXT,  -- JSON string
    intents TEXT,  -- JSON string
    metadata TEXT,  -- JSON string
    
    -- Execution tracking
    execution_order INTEGER,
    parent_nodes TEXT,  -- JSON array as string
    
    -- Timestamps
    registered_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_node_registry_phase ON node_registry(phase);
CREATE INDEX IF NOT EXISTS idx_node_registry_domain ON node_registry(domain);
CREATE INDEX IF NOT EXISTS idx_node_registry_execution_order ON node_registry(execution_order);

-- Updated_at trigger
CREATE TRIGGER IF NOT EXISTS node_registry_updated_at
    AFTER UPDATE ON node_registry
    FOR EACH ROW
BEGIN
    UPDATE node_registry SET updated_at = datetime('now') WHERE node_name = NEW.node_name;
END;

CREATE TABLE IF NOT EXISTS prompts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    version TEXT NOT NULL,
    content TEXT NOT NULL,
    metadata TEXT DEFAULT '{}',
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(name, version)
);

CREATE INDEX IF NOT EXISTS idx_prompts_name ON prompts(name);
CREATE INDEX IF NOT EXISTS idx_prompts_name_created ON prompts(name, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_prompts_version ON prompts(version);
