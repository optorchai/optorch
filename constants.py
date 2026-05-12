class LifecycleHooks:
    PRE_DISPATCH = "pre_dispatch"
    EXECUTE = "execute"
    POST_DISPATCH = "post_dispatch"
    ROUTE = "route"


class ConfigKeys:
    OPTORCH = "optorch"
    NODES = "nodes"
    LLM = "llm"
    SESSION = "session"
    TOOLS = "tools"
    PROMPTS = "prompts"
    INTENTS = "intents"
    PRE_DISPATCH = "pre_dispatch"
    POST_DISPATCH = "post_dispatch"
    ROUTING = "routing"
    RETRY = "retry"
    
    
class SessionBackends:
    MEMORY = "memory"
    POSTGRES = "postgres"
    REDIS = "redis"


class EventTypes:
    MESSAGE = "message"
    TOOL = "tool"
    HISTORY = "history"
    LLM = "llm"
    EMBEDDING = "embedding"
    NODE = "node"
    ERROR = "error"
    LIFECYCLE = "lifecycle"
    SUGGESTIONS = "suggestions"
    TRANSFORMER = "transformer"
    CONFIG = "config"


class RetryDefaults:
    MAX_ATTEMPTS = 3
    BACKOFF_SECONDS = 1
    ON_FAILURE = "halt"


class FailureType:
    HALT = "halt"
    USE_DEFAULTS = "use_defaults"
    SKIP = "skip"
    FALLBACK = "fallback"
    ESCALATE = "escalate"


class NodeAttributes:
    ROUTES = "__routes__"


class StateKeys:
    # core orchestration keys
    SESSION_ID = "session_id"
    USER_MESSAGE = "user_message"
    MESSAGES = "messages"
    ENTITIES = "entities"
    METADATA = "metadata"
    
    # routing keys
    NEXT_NODE = "next_node"
    RETURN_TO = "return_to"
    CURRENT_NODE = "current_node"
    CURRENT_PHASE = "current_phase"
    
    # retry & error handling
    RETRY_FALLBACK = "retry_fallback"
    ERROR = "error"
    RESPONSE = "response"
    
    # interaction & escalation
    NEEDS_USER_INPUT = "needs_user_input"
    USER_CLARIFICATION = "user_clarification"
    PENDING_PHASE = "pending_phase"
    PENDING_PHASE_CONTEXT = "pending_phase_context"

