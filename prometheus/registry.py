from prometheus_client import Counter, Histogram, Gauge, Info, REGISTRY
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST


class MetricsRegistry:
    # prometheus metrics singleton
    
    _instance = None
    _initialized = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
            
        # Request metrics
        self.http_requests_total = Counter(
            'optorch_http_requests_total',
            'Total HTTP requests',
            ['method', 'endpoint', 'status_code']
        )
        
        self.http_request_duration_seconds = Histogram(
            'optorch_http_request_duration_seconds',
            'HTTP request latency',
            ['method', 'endpoint']
        )
        
        # LLM metrics
        self.llm_requests_total = Counter(
            'optorch_llm_requests_total',
            'Total LLM requests',
            ['provider', 'model', 'status']
        )
        
        self.llm_request_duration_seconds = Histogram(
            'optorch_llm_request_duration_seconds',
            'LLM request latency',
            ['provider', 'model']
        )
        
        self.llm_tokens_total = Counter(
            'optorch_llm_tokens_total',
            'Total LLM tokens consumed',
            ['provider', 'model', 'token_type']
        )
        
        self.llm_cost_total = Counter(
            'optorch_llm_cost_total',
            'Total LLM cost by currency',
            ['provider', 'model', 'currency']
        )
        
        # Tool metrics
        self.tool_calls_total = Counter(
            'optorch_tool_calls_total',
            'Total tool calls',
            ['tool_name', 'status']
        )
        
        self.tool_duration_seconds = Histogram(
            'optorch_tool_duration_seconds',
            'Tool execution duration',
            ['tool_name']
        )
        
        # Node metrics
        self.node_executions_total = Counter(
            'optorch_node_executions_total',
            'Total node executions',
            ['node_name', 'status']
        )
        
        self.node_duration_seconds = Histogram(
            'optorch_node_duration_seconds',
            'Node execution duration',
            ['node_name']
        )
        
        self.node_transitions_total = Counter(
            'optorch_node_transitions_total',
            'Total node transitions',
            ['from_node', 'to_node']
        )
        
        # Session metrics
        self.active_sessions = Gauge(
            'optorch_active_sessions',
            'Number of active sessions'
        )
        
        self.session_messages_total = Counter(
            'optorch_session_messages_total',
            'Total messages per session',
            ['session_id']
        )
        
        # History metrics
        self.history_operations_total = Counter(
            'optorch_history_operations_total',
            'Total history operations',
            ['operation', 'status']
        )
        
        self.history_duration_seconds = Histogram(
            'optorch_history_duration_seconds',
            'History operation duration',
            ['operation']
        )
        
        # Error metrics
        self.errors_total = Counter(
            'optorch_errors_total',
            'Total errors',
            ['error_type', 'severity', 'component']
        )
        
        # Cache metrics
        self.cache_operations_total = Counter(
            'optorch_cache_operations_total',
            'Total cache operations',
            ['operation', 'status']
        )
        
        self.cache_hit_rate = Gauge(
            'optorch_cache_hit_rate',
            'Cache hit rate'
        )
        
        # System info
        self.build_info = Info(
            'optorch_build',
            'Build information'
        )
        
        self._initialized = True
    
    @staticmethod
    def get_metrics() -> bytes:
        return generate_latest(REGISTRY)
    
    @staticmethod
    def get_content_type() -> str:
        return CONTENT_TYPE_LATEST
    
    def set_build_info(self, version: str, commit: str = "unknown", branch: str = "unknown"):
        self.build_info.info({
            'version': version,
            'commit': commit,
            'branch': branch
        })
    
    def track_http_request(
        self, 
        method: str, 
        endpoint: str, 
        status_code: int,
        duration: float
    ):
        self.http_requests_total.labels(
            method=method,
            endpoint=endpoint,
            status_code=status_code
        ).inc()
        
        self.http_request_duration_seconds.labels(
            method=method,
            endpoint=endpoint
        ).observe(duration)
    
    def track_llm_request(
        self,
        provider: str,
        model: str,
        status: str,
        duration: float,
        prompt_tokens: int = 0,
        completion_tokens: int = 0,
        cost: float = 0.0,
        currency: str = "USD"
    ):
        self.llm_requests_total.labels(
            provider=provider,
            model=model,
            status=status
        ).inc()
        
        self.llm_request_duration_seconds.labels(
            provider=provider,
            model=model
        ).observe(duration)
        
        if prompt_tokens > 0:
            self.llm_tokens_total.labels(
                provider=provider,
                model=model,
                token_type='prompt'
            ).inc(prompt_tokens)
        
        if completion_tokens > 0:
            self.llm_tokens_total.labels(
                provider=provider,
                model=model,
                token_type='completion'
            ).inc(completion_tokens)
        
        if cost > 0:
            self.llm_cost_total.labels(
                provider=provider,
                model=model,
                currency=currency
            ).inc(cost)
    
    def track_tool_call(
        self,
        tool_name: str,
        status: str,
        duration: float
    ):
        self.tool_calls_total.labels(
            tool_name=tool_name,
            status=status
        ).inc()
        
        self.tool_duration_seconds.labels(
            tool_name=tool_name
        ).observe(duration)
    
    def track_node_execution(
        self,
        node_name: str,
        status: str,
        duration: float
    ):
        self.node_executions_total.labels(
            node_name=node_name,
            status=status
        ).inc()
        
        self.node_duration_seconds.labels(
            node_name=node_name
        ).observe(duration)
    
    def track_node_transition(self, from_node: str, to_node: str):
        self.node_transitions_total.labels(
            from_node=from_node,
            to_node=to_node
        ).inc()
    
    def track_error(
        self,
        error_type: str,
        severity: str,
        component: str
    ):
        self.errors_total.labels(
            error_type=error_type,
            severity=severity,
            component=component
        ).inc()
    
    def update_active_sessions(self, count: int):
        self.active_sessions.set(count)
    
    def track_cache_operation(self, operation: str, status: str):
        self.cache_operations_total.labels(
            operation=operation,
            status=status
        ).inc()
    
    def update_cache_hit_rate(self, rate: float):
        self.cache_hit_rate.set(rate)
