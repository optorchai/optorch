import importlib
from optorch.logging import get_logger
from typing import Any, Callable
from pathlib import Path

logger = get_logger(__name__)


class AutoLoader:
    """auto-loader for any registry (nodes, intents, tools, etc.)"""
    _cache = {}
    
    @staticmethod
    def discover_packages(base_path: str) -> list[str]:
        """Scan directory for packages (dirs with __init__.py) and modules (.py files)"""
        if base_path in AutoLoader._cache:
            return AutoLoader._cache[base_path]
        
        packages = []
        path = Path(base_path)
        
        if path.exists():
            for item in path.iterdir():
                if item.is_dir() and (item / "__init__.py").exists():
                    packages.append(item.name)
                elif item.is_file() and item.suffix == ".py" and item.name != "__init__.py":
                    packages.append(item.stem)
        
        AutoLoader._cache[base_path] = packages
        return packages
    
    @staticmethod
    def import_packages(packages: list[str]) -> None:
        """Import all modules in package tree to trigger decorators"""
        for package in packages:
            try:
                base_path = package.replace(".", "/")
                for item in AutoLoader.discover_packages(base_path):
                    try:
                        importlib.import_module(f"{package}.{item}")
                        sub_path = f"{base_path}/{item}"
                        for sub in AutoLoader.discover_packages(sub_path):
                            try:
                                importlib.import_module(f"{package}.{item}.{sub}")
                            except Exception:
                                pass
                    except Exception:
                        pass
            except Exception:
                pass
    
    @staticmethod
    def load_class(class_name: str, item_name: str, base_package: str) -> type:
        """
        Load class using convention-based discovery.
        
        Tries:
        1. base_package.{item_name} (exact match)
        2. base_package (flat)
        3. All subpackages in base_package
        4. optorch.{type} fallback (e.g., app.intents -> optorch.intents)
        """
        try:
            mod = importlib.import_module(f"{base_package}.{item_name}")
            if hasattr(mod, class_name):
                return getattr(mod, class_name)
        except ImportError:
            pass
        
        try:
            mod = importlib.import_module(base_package)
            if hasattr(mod, class_name):
                return getattr(mod, class_name)
        except (ImportError, AttributeError):
            pass
        
        base_path = base_package.replace(".", "/")
        for pkg in AutoLoader.discover_packages(base_path):
            try:
                mod = importlib.import_module(f"{base_package}.{pkg}")
                if hasattr(mod, class_name):
                    return getattr(mod, class_name)
            except (ImportError, AttributeError):
                continue
        
        if base_package.startswith("app."):
            optorch_package = base_package.replace("app.", "optorch.", 1)
            try:
                return AutoLoader.load_class(class_name, item_name, optorch_package)
            except ImportError:
                pass
        
        raise ImportError(f"Cannot find {class_name} for '{item_name}' in {base_package} or optorch fallback")
    
    @staticmethod
    def register(
        registry: Any, 
        config: dict[str, Any], 
        base_package: str, 
        instantiate: bool = True, 
        namespace: str | None = None,
        metadata_extractor: Callable[[type, str, dict], dict] | None = None
    ) -> tuple[int, int]:
        """
        Auto-register from config with optional metadata extraction.
        
        Args:
            registry: Registry with .register() method
            config: Dict of {name: class_name} or {name: {class: ClassName, ...}}
            base_package: Package to import from (e.g., "app.intents")
            instantiate: If True, call class(); if False, pass class
            namespace: Optional dotted path to nested config (e.g., "budget_adapters.scope")
            metadata_extractor: Optional callback(cls, name, config) -> metadata dict to merge into config
            
        Returns:
            Tuple of (successful_count, failed_count)
        """
        ok = fail = 0
        
        items = config
        if namespace:
            for key in namespace.split("."):
                items = items.get(key, {})
                if not items:
                    logger.warning(f"Namespace '{namespace}' not found in config")
                    return 0, 0
        
        for name, cfg in items.items():
            try:
                if isinstance(cfg, str):
                    class_name = cfg
                    extra_cfg = {}
                else:
                    class_name = cfg.get("class")
                    extra_cfg = dict(cfg) if cfg else {}
                
                if not class_name:
                    logger.warning(f"'{name}' missing 'class', skipped")
                    fail += 1
                    continue
                
                cls = AutoLoader.load_class(class_name, name, base_package)
                
                if metadata_extractor:
                    metadata = metadata_extractor(cls, name, extra_cfg)
                    if metadata:
                        extra_cfg.update(metadata)
                
                item = cls(**extra_cfg) if instantiate else cls
                
                if extra_cfg and not instantiate:
                    import inspect
                    sig = inspect.signature(registry.register)
                    if len(sig.parameters) > 2:
                        registry.register(name, item, extra_cfg)
                    else:
                        registry.register(name, item)
                else:
                    registry.register(name, item)
                
                logger.info(f"✅ {name} ({class_name})")
                ok += 1
                
            except Exception as e:
                logger.error(f"❌ {name}: {e}")
                fail += 1
        
        logger.info(f"Registered {ok} items ({fail} failed)")
        return ok, fail
