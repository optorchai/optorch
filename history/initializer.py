"""history package initializer"""

from optorch.logging import get_logger
from typing import Dict, Any, Optional
from optorch.config import ConfigManager

logger = get_logger(__name__)


class HistoryPackageInitializer:
    """self-contained history initialization"""
    
    @staticmethod
    def initialize(
        config_manager: ConfigManager,
        container: Optional[Any] = None,
        config: Optional[Dict[str, Any]] = None,
        overrides: Optional[Dict[str, Any]] = None
    ) -> Optional[Any]:
        """initialize history system
        
        args:
            config_manager: ConfigManager instance
            container: ApplicationContainer to attach to
            config: optional optorch config dict override
            overrides: optional dict overrides (provider-agnostic)
            
        returns:
            History instance or None
        """
        from optorch.history.config import HistoryConfig, VectorConfig, EmbeddingConfig
        from optorch.initializer_utils import extract_optorch_config
        
        if not container:
            logger.warning("no container provided - history not initialized")
            return None
        
        if hasattr(container, 'history') and container.history:
            logger.debug("history already initialized - skipping")
            return container.history
        
        if not hasattr(container, 'cache_manager') or not container.cache_manager:
            logger.warning("no cache_manager - history not initialized")
            return None
        
        optorch_config = extract_optorch_config(config_manager, config)
        
        config_manager.register_config("history", HistoryConfig)
        config_manager.register_config("vector", VectorConfig)
        config_manager.register_config("embedding", EmbeddingConfig)
        logger.info("✅ history config models registered")
        
        if overrides:
            history_dict = config_manager.merge_overrides("history", overrides, isolate=True)
            vector_dict = config_manager.merge_overrides("vector", overrides, isolate=True)
            embedding_dict = config_manager.merge_overrides("embedding", overrides, isolate=True)
        else:
            history_dict = optorch_config.get("history") or {}
            vector_dict = optorch_config.get("vector")
            embedding_dict = optorch_config.get("embedding")
        
        history_config = HistoryConfig(**history_dict) if history_dict else HistoryConfig()
        vector_cfg = VectorConfig(**vector_dict) if vector_dict else None
        embedding_cfg = EmbeddingConfig(**embedding_dict) if embedding_dict else None
        
        VECTOR_SEARCH_TYPES = {"threshold", "always", "on_demand"}
        needs_vector = False
        for tier in [history_config.short_term, history_config.medium_term, history_config.long_term]:
            if tier and tier.search:
                needs_vector = any(
                    search.get("type") in VECTOR_SEARCH_TYPES 
                    for search in tier.search
                )
                if needs_vector:
                    break
        
        if needs_vector:
            from optorch.embeddings import EmbeddingsRegistry, VectorStoreRegistry
            from optorch.embeddings.providers import OpenAIEmbeddingProvider, OllamaEmbeddingProvider
            from optorch.embeddings.vector_stores import ChromaDBVectorStore, QdrantVectorStore
            
            EmbeddingsRegistry.register("openai", OpenAIEmbeddingProvider)
            EmbeddingsRegistry.register("ollama", OllamaEmbeddingProvider)
            VectorStoreRegistry.register("chromadb", ChromaDBVectorStore)
            VectorStoreRegistry.register("qdrant", QdrantVectorStore)
            logger.debug("registered embedding and vector store providers for history")
            
            if vector_cfg and not history_config.vector:
                history_config.vector = vector_cfg
            if embedding_cfg and not history_config.embedding:
                history_config.embedding = embedding_cfg
            
            if not history_config.vector:
                history_config.vector = VectorConfig()
            if not history_config.embedding:
                history_config.embedding = EmbeddingConfig()
            
            logger.info("enabled vector search for long-term history tier")
        else:
            logger.debug("vector search disabled - not required by search strategy")
        
        from optorch.history.manager import History
        from optorch.history.sources.session import SessionMessageSource
        
        message_source = None
        if hasattr(container, 'session_manager') and container.session_manager:
            message_source = SessionMessageSource(container.session_manager)
        
        history_instance = History(
            config=history_config,
            cache=container.cache_manager,
            source=message_source
        )
        
        container.history = history_instance
        logger.info("✅ history system initialized")
        
        if hasattr(container, 'llm_manager') and container.llm_manager:
                from optorch.history.processors import HistoryRetrieval, HistoryPersistence
                
                executor = container.llm_manager.executor
                executor.register_processor(HistoryRetrieval())
                logger.debug("registered HistoryRetrieval processor")
                
                executor.register_processor(HistoryPersistence())
                logger.debug("registered HistoryPersistence processor")
        
        return history_instance
