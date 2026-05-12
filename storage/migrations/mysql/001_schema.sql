-- MySQL schema for OptOrch
-- Events, interactions, and node registry tables
-- Note: MySQL doesn't support hypertables - using InnoDB with partitioning for time-series data

-- ============================================================================
-- EVENTS TABLE - Time-series event storage
-- ============================================================================
CREATE TABLE IF NOT EXISTS events (
    id BIGINT AUTO_INCREMENT,
    type VARCHAR(255) NOT NULL,
    timestamp_ms BIGINT NOT NULL,
    session_id VARCHAR(255),
    request_id VARCHAR(255),
    user_id VARCHAR(255),
    application_id VARCHAR(255),
    organization_id VARCHAR(255),
    
    -- LLM-specific
    provider VARCHAR(255),
    model VARCHAR(255),
    input_tokens INT,
    output_tokens INT,
    duration_ms INT,
    cost DECIMAL(10, 6),
    currency VARCHAR(10) DEFAULT 'USD',
    
    -- Context
    node_name VARCHAR(255),
    phase VARCHAR(255),
    tool_name VARCHAR(255),
    
    -- Metadata
    metadata JSON,
    
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    
    PRIMARY KEY (id, timestamp_ms),
    INDEX idx_events_session (session_id),
    INDEX idx_events_user (user_id),
    INDEX idx_events_type (type),
    INDEX idx_events_timestamp (timestamp_ms DESC),
    INDEX idx_events_node (node_name),
    INDEX idx_events_currency (currency),
    INDEX idx_events_tool (tool_name),
    INDEX idx_events_org (organization_id),
    INDEX idx_events_org_session (organization_id, session_id),
    INDEX idx_events_org_timestamp (organization_id, timestamp_ms)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================================
-- INTERACTIONS TABLE - User interactions and form submissions
-- ============================================================================
CREATE TABLE IF NOT EXISTS interactions (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    
    -- Multi-tenancy
    session_id VARCHAR(255) NOT NULL,
    user_id VARCHAR(255),
    application_id VARCHAR(255) NOT NULL,
    client_id VARCHAR(255),
    
    -- Timing
    timestamp_ms BIGINT NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    
    -- Interaction metadata
    interaction_type VARCHAR(255),
    node_name VARCHAR(255),
    phase VARCHAR(255),
    
    -- Request/Response
    request JSON NOT NULL,
    response JSON,
    
    -- Budget tracking
    estimated_cost DECIMAL(10, 6),
    actual_cost DECIMAL(10, 6),
    budget_limit DECIMAL(10, 6),
    approved BOOLEAN,
    
    model VARCHAR(255),
    status VARCHAR(50) DEFAULT 'pending' CHECK (status IN ('pending', 'completed', 'rejected')),
    
    metadata JSON,
    
    INDEX idx_interactions_session (session_id),
    INDEX idx_interactions_user (user_id),
    INDEX idx_interactions_application (application_id),
    INDEX idx_interactions_client (client_id),
    INDEX idx_interactions_timestamp (timestamp_ms DESC),
    INDEX idx_interactions_type (interaction_type),
    INDEX idx_interactions_status (status),
    INDEX idx_interactions_app_user (application_id, user_id),
    INDEX idx_interactions_client_session (client_id, session_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='Structured storage for user interactions and form submissions with multi-tenant support';

-- ============================================================================
-- INTERACTION_ENTITIES TABLE - Session entity storage
-- ============================================================================
CREATE TABLE IF NOT EXISTS interaction_entities (
    session_id VARCHAR(255) NOT NULL,
    entity_type VARCHAR(255) NOT NULL,
    entity_data JSON NOT NULL,
    timestamp_ms BIGINT NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (session_id, entity_type),
    INDEX idx_interaction_entities_timestamp (timestamp_ms DESC),
    INDEX idx_interaction_entities_type (entity_type)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='Primary storage for session entities - products, tariffs, entitlements, etc.';

-- ============================================================================
-- NODE_REGISTRY TABLE - Static node configuration
-- ============================================================================
CREATE TABLE IF NOT EXISTS node_registry (
    node_name VARCHAR(255) PRIMARY KEY,
    phase VARCHAR(255),
    domain VARCHAR(255),
    entity_type VARCHAR(255),
    class_name VARCHAR(255) NOT NULL,
    
    -- Routing
    default_route VARCHAR(255),
    route_conditions JSON,
    
    -- Capabilities
    tools JSON,
    llm_model VARCHAR(255),
    streaming BOOLEAN DEFAULT false,
    
    -- Metadata
    prompts JSON,
    intents JSON,
    metadata JSON,
    
    -- Execution tracking
    execution_order INT,
    parent_nodes JSON,
    
    -- Timestamps
    registered_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    INDEX idx_node_registry_phase (phase),
    INDEX idx_node_registry_domain (domain),
    INDEX idx_node_registry_execution_order (execution_order)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='Static node configuration, updated on app startup';
