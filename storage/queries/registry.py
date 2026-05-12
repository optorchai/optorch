from typing import Dict, Type, Tuple, Optional
from pathlib import Path
from optorch.storage.queries.base import BaseQuery
from optorch.logging import get_logger
import importlib
import inspect

logger = get_logger(__name__)


class QueryRegistry:
    """registry for database queries - auto-discovers from queries/ subdirectories"""
    
    def __init__(self):
        self._queries: Dict[Tuple[str, str], Type[BaseQuery]] = {}
        self._auto_discover()
    
    def _auto_discover(self) -> None:
        """scan queries/ subdirs for db-specific query classes"""
        queries_dir = Path(__file__).parent
        self.discover_from_path(queries_dir, "optorch.storage.queries")
    
    def discover_from_path(self, queries_dir: Path, module_prefix: str) -> None:
        """discover and register queries from a given path
        
        supports two patterns:
        1. optorch: queries/{domain}/{store_type}.py -> registers as (store_type, domain)
        2. analytics: queries/{domain}/{query_name}/{store_type}.py -> registers as (store_type, domain.query_name)
        
        args:
            queries_dir: path to queries directory
            module_prefix: python module prefix (e.g., 'optorch.storage.queries')
        """
        if not queries_dir.exists():
            logger.debug(f"queries path not found: {queries_dir}")
            return
        
        for domain_dir in queries_dir.iterdir():
            if not domain_dir.is_dir() or domain_dir.name.startswith("_"):
                continue
            
            domain_name = domain_dir.name
            py_files = list(domain_dir.glob("*.py"))
            has_direct_files = any(not f.name.startswith("_") and f.stem != "base" for f in py_files)
            
            if has_direct_files:
                for py_file in py_files:
                    if py_file.name.startswith("_") or py_file.stem == "base":
                        continue
                    
                    store_type = py_file.stem
                    module_path = f"{module_prefix}.{domain_name}.{store_type}"
                    
                    try:
                        module = importlib.import_module(module_path)
                        
                        for name, obj in inspect.getmembers(module, inspect.isclass):
                            if (issubclass(obj, BaseQuery) and obj is not BaseQuery and obj.__module__ == module_path):
                                self.register(store_type, domain_name, obj)
                                break
                    except Exception as e:
                        logger.warning(f"failed to load query {module_path}: {e}")
            else:
                for query_dir in domain_dir.iterdir():
                    if not query_dir.is_dir() or query_dir.name.startswith("_"):
                        continue
                    
                    query_name = query_dir.name
                    full_query_name = f"{domain_name}.{query_name}"
                    
                    for py_file in query_dir.glob("*.py"):
                        if py_file.name.startswith("_") or py_file.stem == "base":
                            continue
                        
                        store_type = py_file.stem
                        module_path = f"{module_prefix}.{domain_name}.{query_name}.{store_type}"
                        
                        try:
                            module = importlib.import_module(module_path)
                            
                            for name, obj in inspect.getmembers(module, inspect.isclass):
                                if (issubclass(obj, BaseQuery) and obj is not BaseQuery and obj.__module__ == module_path):
                                    self.register(store_type, full_query_name, obj)
                                    break
                        except Exception as e:
                            logger.warning(f"failed to load query {module_path}: {e}")
    
    def register(self, store_type: str, query_name: str, query_class: Type[BaseQuery]) -> None:
        """register query for specific store type"""
        if not issubclass(query_class, BaseQuery):
            raise ValueError(f"{query_class.__name__} must extend BaseQuery")
        
        key = (store_type, query_name)
        self._queries[key] = query_class
        logger.info(f"registered query: ({store_type}, {query_name}) -> {query_class.__name__}")
    
    def get(self, store_type: str, query_name: str) -> Type[BaseQuery]:
        """get query class for store type"""
        key = (store_type, query_name)
        if key not in self._queries:
            raise ValueError(f"query not found: {store_type}.{query_name}")
        return self._queries[key]
    
    def has(self, store_type: str, query_name: str) -> bool:
        """check if query registered"""
        key = (store_type, query_name)
        return key in self._queries
    
    def list_queries(self, store_type: Optional[str] = None) -> list[str]:
        """list all registered queries, optionally filtered by store type"""
        if store_type:
            return [name for (st, name) in self._queries.keys() if st == store_type]
        return [f"{st}.{name}" for (st, name) in self._queries.keys()]
