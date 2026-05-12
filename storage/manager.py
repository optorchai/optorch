import asyncio
from typing import Any, Dict, Optional, Type, Callable, TypeVar, Awaitable, List, TYPE_CHECKING
from optorch.storage.store.base import AbstractStore
from optorch.storage.queries.base import BaseQuery
from optorch.storage.queries.registry import QueryRegistry
from optorch.storage.config import StorageConfig
from optorch.storage.registry import StorageRegistry
from optorch.storage.types import StorageRole
from optorch.storage.resilience import ResilienceRegistry
from optorch.storage.resilience.base import ResilienceStrategy
from optorch.storage.tenant_filter import TenantFilterConfig
from optorch.logging import get_logger

if TYPE_CHECKING:
    from optorch.identity.context import IdentityContext

logger = get_logger(__name__)

T = TypeVar('T')


class StorageManager:
    """central storage manager with role-based access and resilience"""
    
    def __init__(
        self, 
        config: StorageConfig, 
        query_registry: Optional[QueryRegistry] = None,
        resilience_registry: Optional[ResilienceRegistry] = None
    ):
        self.config = config
        self.role = config.role
        self.query_registry = query_registry or QueryRegistry()
        self.resilience_registry = resilience_registry or ResilienceRegistry()
        self.store: Optional[AbstractStore] = None
        self._initialized = False
        self._init_lock = asyncio.Lock()
        self._resilience_pipeline: List[ResilienceStrategy] = []
        self._additional_migrations: Dict[str, str] = {}
        self._namespace_migrations_run: set[str] = set()
        self._migrations_disabled = False
        
        self._setup_resilience_pipeline()
    
    def _setup_resilience_pipeline(self):
        """build resilience strategy pipeline from config"""
        for strategy_name in self.config.resilience_strategies:
            try:
                strategy_class = self.resilience_registry.get(strategy_name)
                strategy_instance = strategy_class.from_config(self.config)
                self._resilience_pipeline.append(strategy_instance)
                logger.debug(f"added resilience strategy: {strategy_name}")
            except Exception as e:
                logger.warning(f"failed to add resilience strategy {strategy_name}: {e}")
    
    async def _execute_with_resilience(self, func: Callable[[], Awaitable[T]]) -> T:
        """wrap function execution with resilience pipeline"""
        if not self._resilience_pipeline:
            return await func()
        
        async def wrapped() -> T:
            result_func = func
            for strategy in reversed(self._resilience_pipeline):
                current = result_func
                
                async def make_wrapper(s: ResilienceStrategy, f: Callable[[], Awaitable[T]]) -> T:
                    return await s.execute(f)
                
                result_func = lambda s=strategy, f=current: make_wrapper(s, f)
            
            return await result_func()
        
        return await wrapped()
    
    def disable_migrations(self, namespace: Optional[str] = None) -> None:
        """disable migrations globally - namespace param ignored, store tracks dedup
        
        args:
            namespace: ignored - provided for API compatibility
        """
        self._migrations_disabled = True
        self.config.migrations_enabled = False
        logger.debug("disabled migrations")
    
    def add_migrations(self, namespace: str, path: str) -> None:
        """register additional migration path for extension
        
        args:
            namespace: migration namespace (e.g., 'notifications', 'analytics')
            path: absolute path to migrations directory
        """
        self._additional_migrations[namespace] = path
        logger.debug(f"registered migration namespace: {namespace} -> {path}")
    
    def remove_migrations(self, namespace: str) -> None:
        """remove migration namespace
        
        args:
            namespace: migration namespace to remove
        """
        if namespace in self._additional_migrations:
            del self._additional_migrations[namespace]
            logger.debug(f"removed migration namespace: {namespace}")
    
    async def run_namespace_migrations(self, namespace: str) -> None:
        """manually run migrations for specific namespace
        
        args:
            namespace: migration namespace to execute
        """
        if namespace not in self._additional_migrations:
            logger.warning(f"migration namespace not registered: {namespace}")
            return
        
        if namespace in self._namespace_migrations_run:
            logger.debug(f"{namespace} migrations already run")
            return
        
        was_disabled = self._migrations_disabled
        self._migrations_disabled = True
        
        await self._ensure_initialized()
        assert self.store is not None
        
        self._migrations_disabled = was_disabled
        
        path = self._additional_migrations[namespace]
        logger.info(f"running {namespace} migrations from {path}")
        original_path = self.config.migrations_path
        self.config.migrations_path = path
        await self.store.run_migrations()
        self.config.migrations_path = original_path
        
        self._namespace_migrations_run.add(namespace)
    
    async def _ensure_initialized(self) -> None:
        """lazy initialization - connect on first use"""
        if self._initialized:
            return
        
        async with self._init_lock:
            if self._initialized:
                return
            
            registry = StorageRegistry()
            store_class = registry.get(self.config.store)
            
            self.store = store_class(self.config)
            
            await self.store.connect()
            logger.debug(f"storage connected: {self.config.store}")
            
            await self.store.prepare()
            
            self._initialized = True
            
            if not self._migrations_disabled and self.config.migrations_enabled:
                await self.store.run_migrations()
            
            if not self._migrations_disabled:
                for namespace, path in self._additional_migrations.items():
                    if namespace in self._namespace_migrations_run:
                        continue
                    logger.info(f"running {namespace} migrations from {path}")
                    original_path = self.config.migrations_path
                    self.config.migrations_path = path
                    
                    original_enabled = self.config.migrations_enabled
                    self.config.migrations_enabled = True
                    await self.store.run_migrations()
                    self.config.migrations_enabled = original_enabled
                    
                    self.config.migrations_path = original_path
                    self._namespace_migrations_run.add(namespace)
    
    async def execute(self, query: str, values: Optional[Dict[str, Any]] = None) -> None:
        """execute write query (requires WRITE role)"""
        if not (self.role & StorageRole.WRITE):
            raise PermissionError("StorageManager does not have WRITE role")
        await self._ensure_initialized()
        assert self.store is not None
        
        await self._execute_with_resilience(
            lambda: self.store.execute(query, values)  # type: ignore
        )
    
    async def fetch_one(self, query: str, values: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        """fetch single row (requires READ role)"""
        if not (self.role & StorageRole.READ):
            raise PermissionError("StorageManager does not have READ role")
        await self._ensure_initialized()
        assert self.store is not None
        
        return await self._execute_with_resilience(
            lambda: self.store.fetch_one(query, values)  # type: ignore
        )
    
    async def fetch_all(self, query: str, values: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """fetch all rows (requires READ role)"""
        if not (self.role & StorageRole.READ):
            raise PermissionError("StorageManager does not have READ role")
        await self._ensure_initialized()
        assert self.store is not None
        
        return await self._execute_with_resilience(
            lambda: self.store.fetch_all(query, values)  # type: ignore
        )
    
    async def fetch_val(self, query: str, values: Optional[Dict[str, Any]] = None, column: int = 0) -> Any:
        """fetch scalar value (requires READ role)"""
        if not (self.role & StorageRole.READ):
            raise PermissionError("StorageManager does not have READ role")
        await self._ensure_initialized()
        assert self.store is not None
        
        return await self._execute_with_resilience(
            lambda: self.store.fetch_val(query, values, column)  # type: ignore
        )
    
    def transaction(self):
        """context manager for transactions"""
        if not self._initialized:
            raise RuntimeError("storage not initialized - call await manager.execute() first")
        assert self.store is not None
        return self.store.transaction()
    
    async def query(self, query_name: str, _identity_context: Optional["IdentityContext"] = None, **kwargs) -> Any:
        """execute registered query with automatic tenant filtering via ambient context
        
        reads organization_id from contextvars (set by authentication middleware)
        automatically injects WHERE organization_id = :org_id for multi-tenant isolation
        
        CONTEXT PROPAGATION:
        
        within same process:
            - ambient context set by middleware flows automatically
            - all storage.query() calls auto-filtered to current user's org
            - zero manual passing required
        
        distributed deployments (analytics/notifications/nodes on different servers):
            - contextvars don't cross network boundaries
            - receiving service must set its own contextvars from headers/metadata
            - OR use _identity_context parameter to bypass ambient context
        
        ambient context flow:
            middleware → sets contextvars → storage reads → filters query → returns tenant data
        
        args:
            query_name: registered query to execute
            _identity_context: optional explicit override (bypasses ambient context)
            **kwargs: query parameters
        
        config control:
            - tenant_filter.enabled: turn on/off automatic filtering
            - tenant_filter.strict_mode: enforce tenant access validation
            - tenant_filter.excluded_tables: skip filtering for specific tables
        """
        await self._ensure_initialized()
        if self.store is None:
            raise RuntimeError("storage not initialized")
        
        filtered_kwargs = kwargs
        
        # tenant filtering: explicit override > ambient context
        if self.config.tenant_filter and self.config.tenant_filter.enabled:
            org_id = None
            
            # 1. explicit override via parameter
            if _identity_context:
                org_id = _identity_context.get_current_org_id()
                logger.debug(f"tenant filter: explicit override org_id={org_id}")
            
            # 2. ambient context (request-scoped via contextvars)
            else:
                from optorch.identity.context import IdentityContext
                org_id = IdentityContext.get_ambient_org_id()
                if org_id:
                    logger.debug(f"tenant filter: ambient context org_id={org_id} query={query_name}")
            
            # inject organization_id if available and not excluded
            if org_id and not self._is_query_excluded(query_name):
                from optorch.storage.tenant_filter import TenantFilter
                tenant_filter = TenantFilter(self.config.tenant_filter)
                filtered_kwargs = tenant_filter.inject(query_name, kwargs, org_id)
        
        store = self.store
        
        async def execute_query():
            query_class = self.query_registry.get(store.store_type, query_name)
            query_instance = query_class(store)
            return await query_instance.execute(**filtered_kwargs)
        
        return await self._execute_with_resilience(execute_query)
    
    def _is_query_excluded(self, query_name: str) -> bool:
        """check if query excluded from tenant filtering"""
        if not self.config.tenant_filter:
            return False
        return query_name in self.config.tenant_filter.excluded_queries
    
    def register_query(self, query_name: str, query_class: Type[BaseQuery]) -> None:
        """register write query for current store type"""
        if not self._initialized:
            logger.debug(f"queuing query registration: {query_name}")
        else:
            assert self.store is not None
            self.query_registry.register(self.store.store_type, query_name, query_class)
            logger.debug(f"registered query: {query_name} for {self.store.store_type}")
    
    @property
    def store_type(self) -> str:
        """return current store type from config"""
        return self.config.store
    
    async def disconnect(self) -> None:
        """close database connection"""
        if self._initialized and self.store:
            await self.store.disconnect()
            logger.info("storage disconnected")
    
    def enable_tenant_filtering(
        self,
        identity_context: "IdentityContext",
        config: Optional[TenantFilterConfig] = None
    ) -> None:
        """enable tenant filtering for multi-tenancy enforcement - deprecated
        
        tenant filtering now configured via StorageConfig.tenant_filter
        middleware sets context automatically via contextvars
        
        args:
            identity_context: deprecated - ambient context used instead
            config: tenant filter configuration
        """
        logger.warning(
            "enable_tenant_filtering() deprecated - set StorageConfig.tenant_filter instead. "
            "middleware sets identity context automatically via contextvars"
        )
        self.config.tenant_filter = config or TenantFilterConfig()
        logger.info("tenant filtering config updated")
    
    def disable_tenant_filtering(self) -> None:
        """disable tenant filtering - deprecated
        
        tenant filtering controlled via StorageConfig.tenant_filter.enabled
        """
        logger.warning("disable_tenant_filter() deprecated - set StorageConfig.tenant_filter.enabled=False")
        if self.config.tenant_filter:
            self.config.tenant_filter.enabled = False
        logger.info("tenant filtering disabled")
    
    def verify_org_access(self, org_id: str) -> bool:
        """verify current user has access to specified organization - deprecated
        
        use identity_context.get_current_org_id() == org_id instead
        
        args:
            org_id: organization ID to check
        
        returns:
            True if user has access, False otherwise
        """
        logger.warning("verify_org_access() deprecated - check IdentityContext.get_ambient_org_id() directly")
        from optorch.identity.context import IdentityContext
        current_org = IdentityContext.get_ambient_org_id()
        return current_org == org_id if current_org else False
