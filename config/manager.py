"""
ConfigManager - multi-namespace config loader with type safety

Auto-discovers all YAML files in config directory
Namespaces by filename: optorch.yaml -> config.optorch
Supports Pydantic validation for typed configs, plain dicts for others
"""
from typing import Any, Optional, Type, Dict, List, TYPE_CHECKING
import os
from datetime import datetime
from pydantic import BaseModel, ValidationError
from optorch.logging import get_logger

from optorch.config.models import CoreConfig
from optorch.config.notifiers import ConfigChangeNotifier, NoOpNotifier
from optorch.config.merger import deep_get, deep_set, deep_merge
from optorch.config.registry import ConfigProviderRegistry
from optorch.config.secrets.registry import SecretProviderRegistry
from optorch.config.provider import ConfigProvider
from optorch.config.secrets.provider import SecretProvider
from optorch.config.reload.registry import ReloadStrategyRegistry
from optorch.config.reload.strategy import ReloadStrategy
from optorch.events.event_types import EventTypes

if TYPE_CHECKING:
    from optorch.events.event_emitter import EventEmitter
    from optorch.transport.ui_transport import UITransportRegistry
    from optorch.transport.base import TransportPublishResponse

logger = get_logger(__name__)


class ConfigManager:
    """Multi-namespace config with auto-discovery and optional type safety"""
    
    def __init__(
        self,
        config_dir: Optional[str] = None,
        config_file: Optional[str] = None,
        config_provider_type: Optional[str] = None,
        secret_provider_type: Optional[str] = None,
        notifier: Optional[ConfigChangeNotifier] = None,
        event_emitter: Optional['EventEmitter'] = None
    ):
        self.config_registry = ConfigProviderRegistry()
        self.secret_registry = SecretProviderRegistry()
        self._event_emitter = event_emitter
        self._transport: Optional['UITransportRegistry'] = None
        
        self.secret_provider: SecretProvider = self.secret_registry.create(
            secret_provider_type or os.getenv("OPTORCH_SECRET_PROVIDER")
        )
        
        provider_type = config_provider_type or os.getenv("OPTORCH_CONFIG_PROVIDER") or "yaml"
        config_dir_resolved = config_dir or os.getenv("OPTORCH_CONFIG_DIR", "config")
        
        self.provider: ConfigProvider = self.config_registry.create(
            provider_type,
            config_dir=config_dir_resolved,
            config_file=config_file,
            secret_provider=self.secret_provider
        )
        
        self._notifier = notifier or NoOpNotifier()  
        self._configs: Dict[str, dict] = {}
        self._models: Dict[str, Type[BaseModel]] = {"optorch": CoreConfig}
        self._runtime_overrides: Dict[str, dict] = {}
        self._extension_defaults: Dict[str, dict] = {}
        self._merged_models: Dict[str, BaseModel] = {}
        self._timestamps: Dict[str, datetime] = {}
        
        self._configs = self.provider.discover()
        
        for namespace in self._configs.keys():
            timestamp = self.provider.get_timestamp(namespace)
            if timestamp:
                self._timestamps[namespace] = timestamp
        
        optorch_typed = self._get_typed_config("optorch")
        if isinstance(optorch_typed, CoreConfig) and optorch_typed.config:
            reload_cfg = optorch_typed.config
            strategy_type = reload_cfg.reload_strategy
            interval = reload_cfg.reload_interval
        else:
            reload_cfg = self._configs.get("optorch", {}).get("config", {})
            strategy_type = reload_cfg.get("reload_strategy", "ttl")
            interval = reload_cfg.get("reload_interval", 60)
        
        self.reload_strategy: ReloadStrategy = ReloadStrategyRegistry.create(
            strategy_type,
            provider=self.provider,
            interval=interval
        )
    
    def get_secret(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """get secret via secret provider
        
        args:
            key: secret key (e.g., "OPENAI_API_KEY")
            default: fallback value
        
        returns:
            secret value or default
        """
        return self.secret_provider.get(key, default)
    
    def set_secret(self, key: str, value: str) -> None:
        """set secret via secret provider (dev/testing)
        
        args:
            key: secret key
            value: secret value
        """
        self.secret_provider.set(key, value)
    
    def merge_overrides(
        self,
        namespace: str,
        overrides: Dict[str, Any] | str | List[str],
        isolate: bool = True
    ) -> Dict[str, Any]:
        """merge config overrides without modifying base
        
        args:
            namespace: target namespace
            overrides: dict (all providers) or file paths (YAML only)
            isolate: if True, return new dict
        
        returns:
            merged config dict
        
        note: critical for library mode - keeps ConfigManager pristine
        """
        return self.provider.merge_overrides(namespace, overrides, isolate)
    
    @property
    def user_config(self) -> dict[str, Any]:
        """All loaded configs as dict"""
        return self._configs
    
    def __getattr__(self, name: str) -> Any:
        """
        Namespace access for configs
        
        Examples:
            config.optorch → CoreConfig instance (Pydantic)
            config.nodes → dict
            config.tools → dict
        
        Note: For hierarchical namespaces use get(): config.get("nodes.node1")
        """
        if name.startswith("_"):
            raise AttributeError(f"'{type(self).__name__}' object has no attribute '{name}'")
        
        if name in self._models:
            return self._get_typed_config(name)
        
        if name not in self._configs:
            raise AttributeError(f"No config namespace: {name}")
        
        return self._get_dict_config(name)
    
    def _get_typed_config(self, namespace: str) -> BaseModel:
        """Get Pydantic model for namespace"""
        if namespace in self._merged_models:
            return self._merged_models[namespace]
        
        model_class = self._models[namespace]
        
        merged = {}
        
        if namespace in self._extension_defaults:
            merged = deep_merge(merged, self._extension_defaults[namespace])
        
        if namespace in self._configs:
            merged = deep_merge(merged, self._configs[namespace])
        
        if namespace in self._runtime_overrides:
            merged = deep_merge(merged, self._runtime_overrides[namespace])

        model = model_class.model_validate(merged)
        self._merged_models[namespace] = model
        return model
    
    def _get_dict_config(self, namespace: str) -> dict:
        """Get dict config with runtime overrides and auto-flattening"""
        config_value = self._configs.get(namespace)
        result = config_value.copy() if config_value is not None else {}
        
        if isinstance(result, dict) and len(result) == 1:
            single_key = list(result.keys())[0]
            if single_key == namespace:
                result = result[single_key]
        
        if namespace in self._runtime_overrides:
            result = deep_merge(result, self._runtime_overrides[namespace])
        
        return result
    
    def _merge_runtime_overrides(self, namespace: str) -> dict:
        """build full namespace config from base + runtime overrides"""
        base = self._configs.get(namespace, {}).copy()
        if namespace in self._runtime_overrides:
            return deep_merge(base, self._runtime_overrides[namespace])
        return base
    
    def get(self, key_path: str, default: Any = None) -> Any:
        """
        Dict-style access across namespaces
        
        Args:
            key_path: Namespace.path format (e.g., "nodes.node1.class", "optorch.llms.default.model")
            default: Default value if key not found
        
        Returns:
            Config value from namespace
        
        Examples:
            config.get("nodes.node1.class") → "Node1Node"
            config.get("optorch.llms.default.model") → "gpt-4"
            config.get("nodes.phased_node") → hierarchical namespace config
        """
        parts = key_path.split(".", 1)
        namespace = parts[0]
        
        if self.reload_strategy.should_reload(namespace, self._timestamps.get(namespace)):
            self._reload_namespace(namespace)
            self.reload_strategy.mark_checked(namespace)
        
        if key_path in self._configs:
            data = self._configs[key_path]
            if isinstance(data, dict) and len(data) == 1:
                single_key = list(data.keys())[0]
                if single_key == key_path:
                    return data[single_key]
            return data
        
        if namespace not in self._configs and namespace in self._models:
            typed = self._get_typed_config(namespace)
            if typed is not None:
                if len(parts) == 1:
                    return typed.model_dump(exclude_none=True) if hasattr(typed, 'model_dump') else typed
                return deep_get(typed.model_dump(exclude_none=True), parts[1], default)
        
        if namespace not in self._configs:
            return default
        
        if len(parts) == 1:
            data = self._configs[namespace]
            if isinstance(data, dict) and len(data) == 1:
                single_key = list(data.keys())[0]
                if single_key == namespace:
                    return data[single_key]
            return data
        
        config_data = self._get_dict_config(namespace)
        return deep_get(config_data, parts[1], default)
    
    def get_hierarchical(self, prefix: str) -> dict[str, Any]:
        """
        Get all configs matching prefix (hierarchical namespace merging).
        
        Handles wrapped structures where YAML has top-level key matching prefix:
        nodes.yaml:                  nodes/phased_node.yaml:
          nodes:                       nodes:
            node1: {...}                phased_node: {...}
            
        Returns flattened {node_name: config} by unwrapping "nodes" key
        """
        merged = {}
        
        for namespace, data in self._configs.items():
            if namespace == prefix or namespace.startswith(f"{prefix}."):
                if isinstance(data, dict) and prefix in data:
                    merged.update(data[prefix])
        
        return merged
    
    def set(self, key_path: str, value: Any, persist: bool = False) -> None:
        """
        Set runtime config value in namespace
        
        Args:
            key_path: Namespace.path format (e.g., "optorch.llms.default.temperature")
            value: New value
            persist: Write to user config file if True
        """
        parts = key_path.split(".", 1)
        namespace = parts[0]
        
        if namespace not in self._configs:
            logger.warning(f"Namespace '{namespace}' not found, creating empty")
            self._configs[namespace] = {}
        
        if namespace not in self._runtime_overrides:
            self._runtime_overrides[namespace] = {}
        
        if len(parts) == 1:
            self._runtime_overrides[namespace] = value
        else:
            deep_set(self._runtime_overrides[namespace], parts[1], value)
        
        if namespace in self._merged_models:
            del self._merged_models[namespace]
        
        logger.info(f"Runtime override: {key_path} = {value}")
        
        if persist:
            full_config = (self._configs.get(namespace) or {}).copy()
            if len(parts) > 1:
                deep_set(full_config, parts[1], value)
            else:
                full_config = value
            self.provider.save(namespace, full_config)
    
    def register_config(
        self, 
        namespace: str, 
        model_class: Type[BaseModel], 
        defaults: Optional[dict] = None
    ) -> None:
        """
        Register Pydantic model for namespace (used by extensions)
        
        Args:
            namespace: Config namespace (e.g., "budget")
            model_class: Pydantic model for validation
            defaults: Default values (merged with model Field defaults)
        
        Example:
            config.register_config("budget", BudgetConfig)
            config.budget.max_amount  # Type-safe access
        """
        self._models[namespace] = model_class
        
        if defaults:
            self._extension_defaults[namespace] = defaults
        
        if namespace in self._merged_models:
            del self._merged_models[namespace]
        
        logger.debug(f"Registered config model for namespace '{namespace}'")
    
    def register_extension_defaults(self, ext_name: str, defaults: dict) -> None:
        """
        Register extension defaults
        
        Extensions typically register under optorch.extensions.{name}
        """
        if "optorch" not in self._extension_defaults:
            self._extension_defaults["optorch"] = {}
        
        if "extensions" not in self._extension_defaults["optorch"]:
            self._extension_defaults["optorch"]["extensions"] = {}
        
        self._extension_defaults["optorch"]["extensions"][ext_name] = defaults
        
        if "optorch" in self._merged_models:
            del self._merged_models["optorch"]
        
        logger.debug(f"Registered extension defaults: {ext_name}")
    
    def validate(self, namespace: Optional[str] = None) -> list[str]:
        """
        Validate config(s) against Pydantic models
        
        Args:
            namespace: Specific namespace to validate, or None for all registered models
        
        Returns:
            List of validation error messages (empty if valid)
        """
        errors = []
        
        namespaces = [namespace] if namespace else self._models.keys()
        
        for ns in namespaces:
            if ns not in self._models:
                continue
            
            try:
                self._get_typed_config(ns)
            except ValidationError as e:
                for err in e.errors():
                    errors.append(f"{ns}: {err}")
        
        return errors
    
    def reload_configs(self) -> None:
        """Reload all configs from disk"""
        self._configs.clear()
        self._merged_models.clear()
        self._timestamps.clear()
        
        self._configs = self.provider.discover()
        
        logger.info("🚀 All configs reloaded")
        
        if self._event_emitter:
            self._event_emitter.emit(f"{EventTypes.CONFIG}.reload", {"namespaces": list(self._configs.keys()), "scope": "all"})
    
    def _reload_namespace(self, namespace: str) -> None:
        """reload single namespace from provider"""
        try:
            config_data = self.provider.load(namespace)
            self._configs[namespace] = config_data
            self._timestamps[namespace] = datetime.now()
            
            if namespace in self._merged_models:
                del self._merged_models[namespace]
            
            logger.info(f"🔥 Hot-reloaded config: {namespace}")
            
            if self._event_emitter:
                self._event_emitter.emit(f"{EventTypes.CONFIG}.reload", {"namespace": namespace, "scope": "namespace"}) 
        except Exception as e:
            logger.warning(f"⚠️ Reload failed for {namespace}: {e}")
    
    def reload_namespace(self, namespace: str) -> None:
        """manually reload namespace (for API endpoints)"""
        self._reload_namespace(namespace)
    
    def set_event_emitter(self, event_emitter: 'EventEmitter') -> None:
        """inject event emitter after initialization (for circular dependency resolution)"""
        self._event_emitter = event_emitter
    
    def _handle_save_request(self, event: dict) -> None:
        """
        All servers (backoffice + runtime) process same event.
        
        Called when receiving config.save event from transport.
        Updates runtime overrides, persists to provider, reloads cache.
        """
        key_path = event["key_path"]
        value = event["value"]
        namespace = key_path.split(".")[0]
        
        self.set(key_path, value, persist=True)
        
        try:
            self._configs[namespace] = self.provider.load(namespace)
            self._timestamps[namespace] = datetime.now()
        except Exception as e:
            logger.warning(f"Failed to reload {namespace} after save: {e}")
        
        if namespace in self._merged_models:
            del self._merged_models[namespace]
        
        if self._event_emitter:
            self._event_emitter.emit(f"{EventTypes.CONFIG}.reload", {
                "namespace": namespace,
                "scope": "namespace"
            })
        
        logger.info(f"Config synced from transport: {namespace}")
    
    async def publish(self, key_path: str, value: Any) -> 'TransportPublishResponse':
        """publish config change to active transport
        
        Args:
            key_path: Config key path (e.g., "nodes.node1.temperature")
            value: New value
        
        Returns:
            Transport acknowledgment
        """
        from optorch.transport.base import TransportPublishResponse
        
        if not self._transport:
            logger.warning("No transport configured - config change not distributed")
            return TransportPublishResponse(status="error", transport="none", error="No transport configured")
        
        active_transport = self._transport.get_active()
        if not active_transport:
            logger.warning("No active transport - config change not distributed")
            return TransportPublishResponse(status="error", transport="none", error="No active transport")
        
        event = {
            "key_path": key_path,
            "value": value
        }
        
        ack = await active_transport.publish(f"{EventTypes.CONFIG}.save", event)
        logger.info(f"Config save event published to active transport: {key_path} - {ack.status}")
        return ack
    
    def set_transport(self, transport: 'UITransportRegistry') -> None:
        """wire transport for distributed config synchronization and subscribe to ALL enabled transports"""
        self._transport = transport
        transport.subscribe_all(f"{EventTypes.CONFIG}.save", self._handle_save_request)
        logger.debug("Transport wired to ConfigManager for distributed config")
    
    def unsubscribe_transports(self) -> None:
        """unsubscribe from all transports - cleanup on shutdown or transport reload"""
        if self._transport:
            self._transport.unsubscribe_all(f"{EventTypes.CONFIG}.save", self._handle_save_request)
            logger.debug("All transport subscriptions cleared")
    
    def enable_notifications(self, notifier: Optional[ConfigChangeNotifier] = None) -> None:
        """Start config change notifier"""
        if notifier:
            self._notifier = notifier
        
        self._notifier.start(on_change=self.reload_configs)
        logger.info("✅ Config change notifications enabled")
    
    def disable_notifications(self) -> None:
        """Stop config change notifier"""
        self._notifier.stop()
        logger.info("❌ Config change notifications disabled")

