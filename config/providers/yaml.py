"""yaml config provider - file-based config with secret resolution"""

import yaml
import re
import os
from typing import Any, Dict, List, Optional
from pathlib import Path
from datetime import datetime
from optorch.logging import get_logger
from optorch.errors.exceptions import ConfigurationError
from optorch.utils import sanitize_path
from optorch.config.secrets.provider import SecretProvider
from optorch.config.secrets.providers.environment import EnvironmentSecretProvider

logger = get_logger(__name__)


class YamlConfigProvider:
    """yaml file-based config provider (refactored ConfigLoader)"""
    
    def __init__(
        self,
        config_dir: str = "config",
        config_file: Optional[str] = None,
        secret_provider: Optional[SecretProvider] = None
    ):
        self.config_dir = Path(config_dir)
        self.config_file = Path(config_file) if config_file else None
        self.secret_provider = secret_provider or EnvironmentSecretProvider()
        self._additional_files: List[Path] = []
        logger.debug(f"yaml provider initialized: dir={self.config_dir}, file={self.config_file}")
    
    def load(self, identifier: str) -> Dict[str, Any]:
        """load yaml file and resolve ${PLACEHOLDERS}
        
        args:
            identifier: namespace (e.g., "optorch", "nodes", "package.config")
                       dots converted to slashes for hierarchical paths
        
        returns:
            config dict with secrets resolved
        
        raises:
            ConfigurationError: file not found or invalid
        """
        path_parts = identifier.replace(".", "/")
        config_path = self.config_dir / f"{path_parts}.yaml"
        
        if not config_path.exists():
            raise ConfigurationError(
                f"config file not found: {identifier}",
                details={
                    "identifier": identifier,
                    "path": str(config_path),
                    "config_dir": str(self.config_dir)
                }
            )
        
        try:
            with open(config_path) as file:
                config = yaml.safe_load(file)
        except Exception as e:
            raise ConfigurationError(
                f"failed to load yaml: {identifier}",
                details={
                    "identifier": identifier,
                    "path": str(config_path),
                    "error": str(e)
                }
            ) from e
        
        sub_config_dir = Path(sanitize_path(str(self.config_dir), identifier))
        if sub_config_dir.exists() and sub_config_dir.is_dir():
            config = self._merge_directory_configs(config, sub_config_dir, identifier)
        
        # resolve secrets
        return self._resolve_secrets(config)
    
    def _merge_directory_configs(
        self,
        base_config: Dict[str, Any],
        config_dir: Path,
        identifier: str
    ) -> Dict[str, Any]:
        """discover and merge yaml files from subdirectory
        
        example:
            config/nodes.yaml + config/nodes/*.yaml → merged into 'nodes' key
        """
        yaml_files = sorted(config_dir.glob("*.yaml"))
        
        if not yaml_files:
            return base_config
        
        if identifier not in base_config:
            base_config[identifier] = {}
        
        for yaml_file in yaml_files:
            try:
                with open(yaml_file) as f:
                    sub_config = yaml.safe_load(f)
                
                if sub_config and identifier in sub_config:
                    for key, value in sub_config[identifier].items():
                        base_config[identifier][key] = value
                    logger.debug(f"merged {yaml_file.name} into {identifier}")
            except Exception as e:
                logger.warning(f"failed to merge {yaml_file}: {e}")
                continue
        
        return base_config
    
    def discover(self, base_identifier: Optional[str] = None) -> Dict[str, Dict[str, Any]]:
        """discover all yaml files in config dir, handle bootstrap, additional files"""
        from optorch.config.merger import deep_merge
        configs = {}
        
        # bootstrap config if provided
        if self.config_file and self.config_file.exists():
            try:
                with open(self.config_file) as f:
                    bootstrap_data = yaml.safe_load(f)
                
                # extract metadata
                if "config" in bootstrap_data and isinstance(bootstrap_data["config"], dict):
                    config_meta = bootstrap_data["config"]
                    
                    if "directory" in config_meta:
                        self.config_dir = Path(config_meta["directory"])
                        logger.info(f"config directory from bootstrap: {self.config_dir}")
                    
                    if "files" in config_meta and isinstance(config_meta["files"], list):
                        self._additional_files = [Path(f) for f in config_meta["files"]]
                        logger.info(f"additional files from bootstrap: {len(self._additional_files)}")
                
                # load bootstrap namespaces
                for namespace, data in bootstrap_data.items():
                    if namespace == "config":
                        continue
                    configs[namespace] = self._resolve_secrets(data)
                
                logger.info(f"loaded bootstrap config: {self.config_file.name}")
            except Exception as e:
                logger.error(f"failed to load bootstrap config {self.config_file}: {e}")
        elif self.config_file:
            logger.warning(f"config file not found: {self.config_file}")
        
        # additional files from bootstrap
        for additional_file in self._additional_files:
            if not additional_file.exists():
                logger.warning(f"additional config file not found: {additional_file}")
                continue
            
            try:
                with open(additional_file) as f:
                    additional_data = yaml.safe_load(f)
                
                for namespace, data in additional_data.items():
                    if namespace == "config":
                        continue
                    if namespace in configs:
                        configs[namespace] = deep_merge(configs[namespace], self._resolve_secrets(data))
                    else:
                        configs[namespace] = self._resolve_secrets(data)
                
                logger.info(f"loaded additional config: {additional_file.name}")
            except Exception as e:
                logger.error(f"failed to load additional config {additional_file}: {e}")
        
        # directory discovery
        if self.config_dir.exists():
            pattern = "*.yaml"
            for yaml_file in self.config_dir.rglob(pattern):
                identifier = self._file_to_namespace(yaml_file)
                
                # skip if already loaded from bootstrap
                if identifier in configs:
                    logger.debug(f"skipping {yaml_file.name} - already loaded from bootstrap")
                    continue
                
                try:
                    with open(yaml_file) as f:
                        config_data = yaml.safe_load(f)
                    configs[identifier] = self._resolve_secrets(config_data)
                    logger.debug(f"discovered namespace '{identifier}' from {yaml_file.name}")
                except Exception as e:
                    logger.warning(f"failed to discover {identifier}: {e}")
                    continue
        else:
            logger.warning(f"config directory not found: {self.config_dir}")
        
        return configs
    
    def _file_to_namespace(self, file_path: Path) -> str:
        """convert file path to namespace
        
        examples:
            optorch.yaml → optorch
            nodes.yaml → nodes
            nodes/product_discovery.yaml → nodes.product_discovery
        """
        rel_path = file_path.relative_to(self.config_dir)
        namespace = str(rel_path.with_suffix("")).replace("/", ".")
        return namespace
    
    def list_namespaces(self, scope: Optional[str] = None) -> List[str]:
        """list config namespaces
        
        args:
            scope: optional filter (e.g., "interactions" returns ["budget", "tariff"])
        
        returns:
            list of namespace names
        """
        yaml_files = list(self.config_dir.glob("*.yaml"))
        namespaces = [f.stem for f in yaml_files]
        
        if scope:
            # hierarchical namespace filtering
            prefix = f"{scope}."
            return [ns.replace(prefix, "") for ns in namespaces if ns.startswith(prefix)]
        
        return namespaces
    
    def save(self, identifier: str, config: Dict[str, Any]) -> None:
        """persist config to yaml file"""
        config_path = self.config_dir / f"{identifier}.yaml"
        
        try:
            self.config_dir.mkdir(parents=True, exist_ok=True)
            with open(config_path, 'w') as file:
                yaml.safe_dump(config, file, default_flow_style=False, sort_keys=False)
            logger.info(f"saved config: {identifier}")
        except Exception as e:
            raise ConfigurationError(
                f"failed to save config: {identifier}",
                details={
                    "identifier": identifier,
                    "path": str(config_path),
                    "error": str(e)
                }
            ) from e
    
    def merge_overrides(
        self,
        namespace: str,
        overrides: Dict[str, Any] | str | List[str],
        isolate: bool = True
    ) -> Dict[str, Any]:
        """merge config overrides without modifying base
        
        args:
            namespace: target namespace
            overrides: dict (all providers) or file path(s) (yaml only)
            isolate: if True, return new dict
        
        returns:
            merged config dict
        """
        # load base
        try:
            base = self.load(namespace)
        except ConfigurationError:
            base = {}
        
        if not isolate:
            result = base
        else:
            from optorch.config.merger import deep_merge
            result = deep_merge({}, base)  # deep copy
        
        # dict overrides
        if isinstance(overrides, dict):
            from optorch.config.merger import deep_merge
            return deep_merge(result, overrides)
        
        # file path overrides
        if isinstance(overrides, str):
            overrides = [overrides]
        
        if isinstance(overrides, list):
            for path_str in overrides:
                path = Path(path_str)
                if not path.exists():
                    logger.warning(f"override file not found: {path_str}")
                    continue
                
                try:
                    with open(path) as f:
                        override_data = yaml.safe_load(f)
                    
                    if namespace in override_data:
                        from optorch.config.merger import deep_merge
                        result = deep_merge(result, override_data[namespace])
                    
                    logger.debug(f"merged override from {path_str}")
                except Exception as e:
                    logger.warning(f"failed to load override {path_str}: {e}")
                    continue
        
        return result
    
    def _resolve_secrets(self, config: Any) -> Any:
        """recursively resolve ${SECRET} placeholders"""
        if isinstance(config, dict):
            return {k: self._resolve_secrets(v) for k, v in config.items()}
        elif isinstance(config, list):
            return [self._resolve_secrets(v) for v in config]
        elif isinstance(config, str):
            return self._substitute_placeholders(config)
        return config
    
    def _substitute_placeholders(self, value: str) -> str:
        """replace ${KEY} or ${KEY:default} with secret
        
        examples:
            "${OPENAI_API_KEY}" → "sk-..."
            "${GROQ_API_KEY:fallback}" → secret or "fallback"
            "postgresql://${DB_USER}:${DB_PASSWORD}@host/db" → resolved
        """
        pattern = r'\$\{([^:}]+)(?::([^}]+))?\}'
        
        def replacer(match):
            key = match.group(1).strip()
            default = match.group(2).strip() if match.group(2) else None
            
            secret = self.secret_provider.get(key, default=default)
            
            if secret is None:
                raise ConfigurationError(
                    f"secret not found: {key}",
                    details={
                        "secret_key": key,
                        "placeholder": match.group(0)
                    }
                )
            
            return secret
        
        return re.sub(pattern, replacer, value)
    
    def get_timestamp(self, namespace: str) -> Optional[datetime]:
        """get last modification time of yaml file"""
        path_parts = namespace.replace(".", "/")
        config_path = self.config_dir / f"{path_parts}.yaml"
        
        if not config_path.exists():
            return None
        
        try:
            mtime = os.path.getmtime(config_path)
            return datetime.fromtimestamp(mtime)
        except Exception as e:
            logger.debug(f"failed to get timestamp for {namespace}: {e}")
            return None
