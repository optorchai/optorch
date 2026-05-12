-- TimescaleDB schema for OptOrch
-- Events, interactions, and node registry tables with hypertable optimization

-- Enable TimescaleDB extension
CREATE EXTENSION IF NOT EXISTS timescaledb;

-- ============================================================================
-- EVENTS TABLE - Time-series event storage
-- ============================================================================
CREATE TABLE IF NOT EXISTS events (
    id BIGSERIAL,
    type TEXT NOT NULL,
    timestamp_ms BIGINT NOT NULL,
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
    cost DECIMAL(10, 6),
    currency TEXT DEFAULT 'USD',
    
    -- Context
    node_name TEXT,
    phase TEXT,
    tool_name TEXT,
    
    -- Metadata
    metadata JSONB,
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    PRIMARY KEY (id, timestamp_ms)
);

-- Convert to hypertable (1 day chunks)
SELECT create_hypertable('events', 'timestamp_ms', chunk_time_interval => 86400000, if_not_exists => TRUE);

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

-- Enable compression
ALTER TABLE events SET (
    timescaledb.compress,
    timescaledb.compress_segmentby = 'session_id,type'
);

-- ============================================================================
-- INTERACTIONS TABLE - User interactions and form submissions
-- ============================================================================
CREATE TABLE IF NOT EXISTS interactions (
    id BIGSERIAL PRIMARY KEY,
    
    -- Multi-tenancy
    session_id TEXT NOT NULL,
    user_id TEXT,
    application_id TEXT NOT NULL,
    client_id TEXT,
    
    -- Timing
    timestamp_ms BIGINT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Interaction metadata
    interaction_type TEXT,
    node_name TEXT,
    phase TEXT,
    
    -- Request/Response
    request JSONB NOT NULL,
    response JSONB,
    
    -- Budget tracking
    estimated_cost DECIMAL(10, 6),
    actual_cost DECIMAL(10, 6),
    budget_limit DECIMAL(10, 6),
    approved BOOLEAN,
    
    model TEXT,
    status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'completed', 'rejected')),
    
    metadata JSONB
);

-- Convert to hypertable
SELECT create_hypertable('interactions', 'timestamp_ms', chunk_time_interval => 86400000, if_not_exists => TRUE);

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

-- Enable compression
ALTER TABLE interactions SET (
    timescaledb.compress,
    timescaledb.compress_segmentby = 'application_id,client_id,session_id'
);

COMMENT ON TABLE interactions IS 'Structured storage for user interactions and form submissions with multi-tenant support';

-- ============================================================================
-- INTERACTION_ENTITIES TABLE - Session entity storage
-- ============================================================================
CREATE TABLE IF NOT EXISTS interaction_entities (
    session_id TEXT NOT NULL,
    entity_type TEXT NOT NULL,
    entity_data JSONB NOT NULL,
    timestamp_ms BIGINT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (session_id, entity_type)
);

CREATE INDEX IF NOT EXISTS idx_interaction_entities_timestamp ON interaction_entities(timestamp_ms DESC);
CREATE INDEX IF NOT EXISTS idx_interaction_entities_type ON interaction_entities(entity_type);
CREATE INDEX IF NOT EXISTS idx_interaction_entities_data ON interaction_entities USING GIN(entity_data);

COMMENT ON TABLE interaction_entities IS 'Primary storage for session entities - products, tariffs, entitlements, etc.';

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
    route_conditions JSONB,
    
    -- Capabilities
    tools JSONB,
    llm_model TEXT,
    streaming BOOLEAN DEFAULT false,
    
    -- Metadata
    prompts JSONB,
    intents JSONB,
    metadata JSONB,
    
    -- Execution tracking
    execution_order INTEGER,
    parent_nodes TEXT[],
    
    -- Timestamps
    registered_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_node_registry_phase ON node_registry(phase);
CREATE INDEX IF NOT EXISTS idx_node_registry_domain ON node_registry(domain);
CREATE INDEX IF NOT EXISTS idx_node_registry_execution_order ON node_registry(execution_order);

-- Updated_at trigger
CREATE OR REPLACE FUNCTION update_node_registry_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS node_registry_updated_at ON node_registry;
CREATE TRIGGER node_registry_updated_at
    BEFORE UPDATE ON node_registry
    FOR EACH ROW
    EXECUTE FUNCTION update_node_registry_timestamp();

COMMENT ON TABLE node_registry IS 'Static node configuration, updated on app startup';
COMMENT ON COLUMN node_registry.execution_order IS 'Depth in execution tree (0=entry nodes)';
COMMENT ON COLUMN node_registry.parent_nodes IS 'Array of node names that can route to this node';
