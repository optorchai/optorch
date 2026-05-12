"""history manager"""

from typing import Any, Dict, List, Optional, TYPE_CHECKING
from optorch.logging import get_logger
from optorch.messaging import Message, MessageContext, MessageSource
from optorch.cache import CacheManager
from optorch.history.config import HistoryConfig, HistoryLayerConfig
from optorch.history.filters import FilterRegistry, CompositeFilter
from optorch.history.constants import MEMORY_TYPES, STORAGE_TYPES, SEARCH_TYPES, FILTER_TYPES
from optorch.events import emits, EventTypes
from optorch.errors import ConfigurationError

if TYPE_CHECKING:
    from optorch.history.storage.base import StorageStrategy
    from optorch.history.search.base import SearchStrategy
    from optorch.embeddings import BaseVectorStore

logger = get_logger(__name__)


class History:
    
    def __init__(
        self,
        config: HistoryConfig,
        cache: Optional[CacheManager] = None,
        source: Optional[MessageSource] = None
    ) -> None:
        self.config: HistoryConfig = config
        self.cache: Optional[CacheManager] = cache
        self.source: Optional[MessageSource] = source
        self.vector_store: Optional['BaseVectorStore'] = None
        self._filter_registry: FilterRegistry = FilterRegistry()
        self._init_filters()
        
        self._memory: Optional[Any] = None
        self._storage: Optional['StorageStrategy'] = None
        self._search: Optional['SearchStrategy'] = None
        self._filter: Optional[CompositeFilter] = None
    
    def _get_vector_store(self) -> Optional['BaseVectorStore']:
        """Lazy initialization of vector store - only when actually needed"""
        if self.vector_store is None and self.config.embedding and self.config.vector:
            try:
                from optorch.embeddings import EmbeddingsRegistry, VectorStoreRegistry
                
                embedding_provider = EmbeddingsRegistry.get(
                    self.config.embedding.provider,
                    **self.config.embedding.params
                )
                
                self.vector_store = VectorStoreRegistry.get(
                    self.config.vector.provider,
                    embedding_provider,
                    **self.config.vector.params
                )
                
                logger.info(f"Initialized {self.config.vector.provider} vector store with {self.config.embedding.provider} embeddings")
            except Exception as e:
                logger.warning(f"Vector search unavailable: {e}")
        
        return self.vector_store
    
    def _init_filters(self) -> None:
        for name, class_path in FILTER_TYPES.items():
            filter_class = self._load_class(class_path)
            self._filter_registry.register(name, filter_class)
    
    @staticmethod
    def _load_class(class_path: str) -> Any:
        module_path, class_name = class_path.rsplit(".", 1)
        module = __import__(module_path, fromlist=[class_name])
        return getattr(module, class_name)
    
    def _get_memory(self) -> Any:
        if self._memory is None:
            tier = self.config.short_term or HistoryLayerConfig()
            if not tier.memory:
                raise ConfigurationError("No memory configuration provided")
            
            config = tier.memory[0]
            memory_type = config.get("type", "smart_window")
            params = config.get("params", {})
            
            class_path = MEMORY_TYPES.get(memory_type)
            if not class_path:
                raise ConfigurationError(f"Unknown memory type: {memory_type}")
            
            cls = self._load_class(class_path)
            self._memory = cls(**params)
        
        return self._memory
    
    def _get_storage(self) -> 'StorageStrategy':
        if self._storage is None:
            tier = self.config.short_term or HistoryLayerConfig()
            if not tier.storage:
                raise ConfigurationError("No storage configuration provided")
            
            if not self.source:
                raise ConfigurationError("MessageSource required but none provided")
            
            config = tier.storage[0]
            storage_type = config.get("type", "raw")
            params = config.get("params", {})
            
            class_path = STORAGE_TYPES.get(storage_type)
            if not class_path:
                raise ConfigurationError(f"Unknown storage type: {storage_type}")
            
            cls = self._load_class(class_path)
            class_name = class_path.split(".")[-1]
            
            if class_name == "FilteredStorage":
                self._storage = cls(source=self.source, filter=self._get_filter())
            elif class_name in ["RawStorage", "SummaryStorage", "HybridStorage"]:
                self._storage = cls(source=self.source)
            else:
                self._storage = cls(**params)
        
        assert self._storage is not None
        return self._storage
    
    def _get_search(self) -> Optional['SearchStrategy']:
        tier = self.config.long_term or HistoryLayerConfig()
        if self._search is None and tier.search:
            config = tier.search[0]
            search_type = config.get("type", "never")
            params = config.get("params", {})
            
            class_path = SEARCH_TYPES.get(search_type)
            if not class_path:
                raise ConfigurationError(f"Unknown search type: {search_type}")
            
            cls = self._load_class(class_path)
            self._search = cls(**params)
        
        return self._search
    
    def _get_filter(self) -> Optional[CompositeFilter]:
        tier = self.config.short_term or HistoryLayerConfig()
        if self._filter is None and tier.filters:
            filter_configs = tier.filters if isinstance(tier.filters, list) else []
            filter_instances = []
            for f in filter_configs:
                if isinstance(f, dict):
                    filter_type = f.get("type")
                    if filter_type is not None:
                        filter_instances.append(
                            self._filter_registry.create(filter_type, **f.get("params", {}))
                        )
            if filter_instances:
                self._filter = CompositeFilter(filter_instances)
        
        return self._filter
    
    async def context(self, ctx: MessageContext) -> List[Message]:
        if self.cache and self.config.cache_enabled:
            cache_key = f"history:{ctx.session_id}"
            cached = await self.cache.get(cache_key)
            if cached:
                return [Message.from_dict(m) for m in cached]
        
        all_messages = await self._get_storage().load(ctx)
        messages = self._apply_tier_processing(all_messages)
        messages = self._get_memory().get_messages(messages)

        message_filter = self._get_filter()
        if message_filter:
            messages = message_filter.filter(messages)
        
        messages = ctx.apply_limit(messages)
        
        if self.cache and self.config.cache_enabled:
            await self.cache.set(cache_key, [m.to_dict() for m in messages])
        
        return messages
    
    def _apply_tier_processing(self, messages: List[Message]) -> List[Message]:
        """Apply tier-specific strategies to messages based on recency
        
        Splits messages into tiers:
        - Recent (last N messages): short_term tier (no additional filtering)
        - Older (beyond threshold): medium_term tier (apply medium_term.filters)
        """
        if not messages or not self.config.medium_term:
            return messages
        
        total = len(messages)
        threshold = self.config.tier_threshold
        
        if total <= threshold:
            return messages
        
        short_messages = messages[-threshold:]
        medium_messages = messages[:-threshold]
        
        medium_tier = self.config.medium_term
        if medium_tier.filters:
            medium_filter = self._create_filter_for_tier(medium_tier.filters)
            if medium_filter:
                medium_messages = medium_filter.filter(medium_messages)
        
        return medium_messages + short_messages
    
    def _create_filter_for_tier(self, filter_configs: List[Dict[str, Any]]) -> Optional[CompositeFilter]:
        """Create composite filter from tier-specific filter configs"""
        filter_instances = []
        for config in filter_configs:
            if isinstance(config, dict):
                filter_type = config.get("type")
                params = config.get("params", {})
                if filter_type:
                    filter_instance = self._filter_registry.create(filter_type, **params)
                    filter_instances.append(filter_instance)
        
        return CompositeFilter(filter_instances) if filter_instances else None
    
    async def save(self, messages: List[Message], ctx: MessageContext) -> None:
        """Save messages to history"""
        storage = self._get_storage()
        await storage.save(messages, ctx)
        
        if self.cache and self.config.cache_enabled:
            cache_key = f"history:{ctx.session_id}"
            await self.cache.delete(cache_key)
        
        if self.vector_store:
            await self.vector_store.index_messages(messages, ctx)
    
    async def _vector_search(self, query: str, ctx: MessageContext) -> Optional[List[Message]]:
        vector_store = self._get_vector_store()
        if not vector_store:
            logger.warning("Vector search requested but vector store unavailable")
            return None
        
        storage = self._get_storage()
        all_messages = await storage.load(ctx)
        
        if not all_messages:
            return None
        
        limit = ctx.metadata.get("vector_search_limit", 10)
        threshold = ctx.metadata.get("vector_search_threshold", 0.7)
        
        return await vector_store.search(query, all_messages, ctx, limit, threshold)
    
    async def search(
        self,
        query: str,
        ctx: MessageContext
    ) -> Optional[List[Message]]:
        search = self._get_search()
        if not search:
            return None
        return await search.search(query, ctx, self._vector_search)
    
    async def get_messages(self, session_id: str) -> List[Dict[str, Any]]:
        """Load history as dicts for LLM consumption"""
        messages = await self.context(MessageContext(session_id=session_id))
        return [m.to_dict() for m in messages]
