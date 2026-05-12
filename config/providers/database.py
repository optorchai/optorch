"""database config provider - runtime updates with hot-reload"""

import asyncio
from typing import TYPE_CHECKING, Any, Dict, List, Optional
from datetime import datetime
from optorch.logging import get_logger
from optorch.errors.exceptions import ConfigurationError
from optorch.config.provider import ConfigProvider
from optorch.config.secrets.provider import SecretProvider
from optorch.config.secrets.providers.environment import EnvironmentSecretProvider
from optorch.storage.manager import StorageManager
from optorch.storage.queries.registry import QueryRegistry

if TYPE_CHECKING:
    from optorch.identity.context import IdentityContext

logger = get_logger(__name__)


class DatabaseConfigProvider(ConfigProvider):
    """database-backed config provider for runtime updates with multi-tenancy
    
    uses own storage instance with config queries only
    physically isolated from general storage_manager
    """
    
    def __init__(
        self,
        secret_provider: Optional[SecretProvider] = None,
        fallback_provider: Optional[ConfigProvider] = None,
        identity_context: Optional["IdentityContext"] = None
    ):
        self.secret_provider = secret_provider or EnvironmentSecretProvider()
        self.fallback_provider = fallback_provider
        self.identity_context = identity_context
        self._db_ready = False
        self.storage = self._create_storage()
        logger.debug("database provider initialized (using fallback until DB ready)")
    
    def _create_storage(self) -> Optional[StorageManager]:
        """create storage with manually registered config queries"""
        if not self.fallback_provider:
            logger.warning("no fallback provider - database config provider needs fallback for bootstrap")
            return None
        
        try:
            import importlib
            from optorch.storage.config import StorageConfig
            
            storage_config_dict = self.fallback_provider.load("storage")
            
            connection_string_key = storage_config_dict.get("connection_string")
            if connection_string_key:
                resolved = self.secret_provider.get(connection_string_key)
                if resolved:
                    storage_config_dict["connection_string"] = resolved
                    logger.debug(f"resolved storage connection_string from secret: {connection_string_key}")
            
            storage_config_dict["migrations_enabled"] = False  # config owns its migrations
            storage_config = StorageConfig(**storage_config_dict)
            backend = storage_config.store
            
            registry = QueryRegistry()
            query_names = ["get_config", "save_config", "list_configs", "get_config_timestamp"]
            
            for query_name in query_names:
                module_path = f"optorch.config.queries.{query_name}.{backend}"
                module = importlib.import_module(module_path)
                query_class = getattr(module, f"{query_name.title().replace('_', '')}Query")
                registry.register(backend, query_name, query_class)
            
            storage = StorageManager(config=storage_config, query_registry=registry)
            
            # register config migrations - run on first load() call
            import os
            migrations_path = os.path.join(os.path.dirname(__file__), "..", "migrations")
            storage.add_migrations("config", migrations_path)
            logger.debug(f"config storage created with migrations from {migrations_path} (lazy init)")
            
            return storage
        except Exception as e:
            logger.warning(f"config storage init failed: {e}")
            return None
    
    def _get_organization_id(self) -> Optional[str]:
        """get current organization_id from identity context"""
        if not self.identity_context:
            return None
        
        try:
            return self.identity_context.get_current_org_id()
        except Exception as e:
            logger.debug(f"failed to get organization_id from context: {e}")
            return None
    
    def load(self, identifier: str) -> Dict[str, Any]:
        """load from database (tenant-specific or global), fallback to yaml if not found
        
        during bootstrap (before initialize_async), always uses fallback.
        after DB ready, queries DB first, then fallback.
        """
        # use fallback during bootstrap
        if not self._db_ready:
            if not self.fallback_provider:
                raise ConfigurationError("DB not ready and no fallback provider", details={"identifier": identifier})
            return self.fallback_provider.load(identifier)
        
        # DB ready - try DB first
        if not self.storage or not self.storage.store:
            if not self.fallback_provider:
                raise ConfigurationError("no storage or fallback provider", details={"identifier": identifier})
            return self.fallback_provider.load(identifier)
        
        try:
            org_id = self._get_organization_id()
            
            query_class = self.storage.query_registry.get(self.storage.store_type, "get_config")
            query_instance = query_class(self.storage.store)
            result = asyncio.run(query_instance.execute(namespace=identifier, organization_id=org_id))
            
            if result:
                return result["config_data"]
            
            if self.fallback_provider:
                logger.debug(f"config not in db, loading from fallback: {identifier}")
                return self.fallback_provider.load(identifier)
            
            raise ConfigurationError(f"config not found: {identifier}")
        except Exception as e:
            if self.fallback_provider:
                logger.warning(f"database load failed, using fallback: {e}")
                return self.fallback_provider.load(identifier)
            raise
    
    def discover(self, base_identifier: Optional[str] = None) -> Dict[str, Dict[str, Any]]:
        """discover configs from database (tenant-specific + global), merge with fallback (db overrides fallback)
        
        during bootstrap, returns fallback only.
        after DB ready, merges DB + fallback.
        """
        result = {}
        
        if self.fallback_provider:
            result = self.fallback_provider.discover(base_identifier)
        
        # only query DB if ready
        if self._db_ready and self.storage and self.storage.store:
            try:
                org_id = self._get_organization_id()
                
                query_class = self.storage.query_registry.get(self.storage.store_type, "list_configs")
                query_instance = query_class(self.storage.store)
                db_configs = asyncio.run(query_instance.execute(prefix=base_identifier, organization_id=org_id))
                
                for config in db_configs:
                    result[config["namespace"]] = config["config_data"]
            except Exception as e:
                logger.warning(f"database discover failed: {e}")
        
        return result
    
    def list_namespaces(self, scope: Optional[str] = None) -> List[str]:
        """list namespaces from database (tenant-specific + global) + fallback
        
        during bootstrap, returns fallback only.
        after DB ready, merges DB + fallback.
        """
        namespaces = set()
        
        # only query DB if ready
        if self._db_ready and self.storage and self.storage.store:
            try:
                org_id = self._get_organization_id()
                
                query_class = self.storage.query_registry.get(self.storage.store_type, "list_configs")
                query_instance = query_class(self.storage.store)
                db_configs = asyncio.run(query_instance.execute(prefix=scope, organization_id=org_id))
                namespaces.update(config["namespace"] for config in db_configs)
            except Exception as e:
                logger.warning(f"database list failed: {e}")
        
        if self.fallback_provider:
            namespaces.update(self.fallback_provider.list_namespaces(scope))
        
        return list(namespaces)
    
    def save(self, identifier: str, config: Dict[str, Any]) -> None:
        """save config to database (tenant-specific if org context available)
        
        raises ConfigurationError if DB not ready (call initialize_async first)
        """
        if not self._db_ready:
            raise ConfigurationError("database not ready - call initialize_async() before save()", details={"identifier": identifier})
        
        if not self.storage or not self.storage.store:
            raise ConfigurationError("storage not initialized", details={"identifier": identifier})
        
        org_id = self._get_organization_id()
        
        query_class = self.storage.query_registry.get(self.storage.store_type, "save_config")
        query_instance = query_class(self.storage.store)
        asyncio.run(query_instance.execute(namespace=identifier, config_data=config, organization_id=org_id))
        logger.info(f"saved config to db: {identifier} (org={org_id or 'global'})")
    
    def merge_overrides(
        self,
        namespace: str,
        overrides: Dict[str, Any] | str | List[str],
        isolate: bool = True
    ) -> Dict[str, Any]:
        """merge via fallback"""
        if not self.fallback_provider:
            raise ConfigurationError(
                "database provider requires fallback_provider",
                details={"namespace": namespace}
            )
        return self.fallback_provider.merge_overrides(namespace, overrides, isolate)
    
    def get_timestamp(self, namespace: str) -> Optional[datetime]:
        """get last-updated timestamp from db (tenant-specific or global)
        
        returns None if DB not ready or no timestamp available
        """
        if not self._db_ready or not self.storage or not self.storage.store:
            return None
        
        try:
            org_id = self._get_organization_id()
            
            query_class = self.storage.query_registry.get(self.storage.store_type, "get_config_timestamp")
            query_instance = query_class(self.storage.store)
            result = asyncio.run(query_instance.execute(namespace=namespace, organization_id=org_id))
            
            if result and "updated_at" in result:
                return result["updated_at"]
        except Exception as e:
            logger.debug(f"timestamp fetch failed for {namespace}: {e}")
        
        return None
    
    async def initialize_async(self) -> None:
        """explicitly initialize storage and run migrations
        
        MUST be called during app startup before DB queries.
        sets _db_ready flag to enable DB queries.
        """
        if self.storage:
            await self.storage._ensure_initialized()
            self._db_ready = True
            logger.info("config storage initialized and migrations complete - DB ready for queries")
