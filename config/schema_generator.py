"""config schema generation from pydantic models"""

import json
import importlib
import inspect
from pathlib import Path
from typing import Dict, Optional
from pydantic import BaseModel

try:
    from importlib.metadata import distributions
except ImportError:
    from importlib_metadata import distributions  # py < 3.8


def _extract_config_schema(module) -> Optional[tuple[str, dict]]:
    """extract first config class schema from module"""
    for name, obj in inspect.getmembers(module, inspect.isclass):
        if name.endswith("Config") and issubclass(obj, BaseModel) and obj is not BaseModel:
            return name, obj.model_json_schema()
    return None


def _extract_all_config_schemas(module) -> Dict[str, dict]:
    """extract all config class schemas from module"""
    schemas = {}
    for name, obj in inspect.getmembers(module, inspect.isclass):
        if name.endswith("Config") and issubclass(obj, BaseModel) and obj is not BaseModel:
            key = name.replace("Config", "").lower()
            schemas[key] = obj.model_json_schema()
    return schemas


def discover_extension_configs() -> Dict[str, dict]:
    """auto-discover config classes from installed packages and local extensions"""
    extension_schemas = {}
    
    # scan installed packages
    for dist in distributions():
        if not dist.metadata:
            continue
            
        package_name = dist.metadata.get("Name")
        if not package_name:
            continue
        
        for pattern in [f"{package_name}.config", f"{package_name}_extension.config"]:
            try:
                module = importlib.import_module(pattern)
                result = _extract_config_schema(module)
                if result:
                    schema_name = package_name.replace("-", "_")
                    extension_schemas[schema_name] = result[1]
                    break
            except (ImportError, AttributeError, ValueError):
                continue
    
    # scan local extensions dir for dev mode
    try:
        current = Path(__file__).parent
        while current.parent != current:
            if (current / "extensions").exists():
                extensions_dir = current / "extensions"
                break
            current = current.parent
        else:
            return extension_schemas
        
        for ext_path in extensions_dir.iterdir():
            if not ext_path.is_dir() or ext_path.name.startswith("_"):
                continue
            
            config_file = ext_path / "config.py"
            if not config_file.exists():
                continue
            
            try:
                module = importlib.import_module(f"extensions.{ext_path.name}.config")
                result = _extract_config_schema(module)
                if result:
                    extension_schemas[ext_path.name] = result[1]
            except (ImportError, AttributeError):
                pass
    except Exception:
        pass
    
    return extension_schemas


def discover_core_configs() -> Dict[str, dict]:
    """auto-discover core optorch and api configs"""
    core_schemas = {}
    
    try:
        from optorch.config.models import CoreConfig
        core_schemas["optorch"] = CoreConfig.model_json_schema()
    except (ImportError, AttributeError):
        pass
    
    current = Path(__file__).parent
    while current.parent != current:
        if (current / "optorch").exists() and (current / "api").exists():
            project_root = current
            break
        current = current.parent
    else:
        return core_schemas
    
    optorch_dir = project_root / "optorch"
    if optorch_dir.exists():
        for subdir in optorch_dir.iterdir():
            if not subdir.is_dir() or subdir.name.startswith("_"):
                continue
            
            config_file = subdir / "config.py"
            if not config_file.exists():
                continue
            
            try:
                module = importlib.import_module(f"optorch.{subdir.name}.config")
                result = _extract_config_schema(module)
                if result:
                    class_name = result[0]
                    key = class_name.replace("Config", "").lower()
                    if key.startswith("llm"):
                        key = class_name.lower().replace("config", "")
                    core_schemas[key] = result[1]
            except (ImportError, AttributeError):
                pass
    
    api_config = project_root / "api" / "config.py"
    if api_config.exists():
        try:
            module = importlib.import_module("api.config")
            result = _extract_config_schema(module)
            if result:
                core_schemas["api"] = result[1]
        except (ImportError, AttributeError):
            pass
    
    try:
        module = importlib.import_module("optorch.controller.node_config")
        controller_schemas = _extract_all_config_schemas(module)
        core_schemas.update(controller_schemas)
    except (ImportError, AttributeError):
        pass
    
    return core_schemas


def generate_schemas(output_dir: Optional[Path] = None) -> int:
    """generate json schema documentation for all config classes"""
    
    schemas = {}
    
    core_schemas = discover_core_configs()
    schemas.update(core_schemas)
    
    extension_schemas = discover_extension_configs()
    schemas.update(extension_schemas)
    
    if output_dir is None:
        current = Path(__file__).parent
        while current.parent != current:
            if (current / "docs").exists() or current.name == "Orchestrator":
                output_dir = current / "docs"
                break
            current = current.parent
        else:
            output_dir = Path.cwd() / "docs"
    
    output_dir.mkdir(exist_ok=True)
    
    schema_file = output_dir / "config-schema.json"
    with open(schema_file, "w") as f:
        json.dump(schemas, f, indent=2)
    
    print(f"✅ Generated config schema: {schema_file}")
    print(f"📊 Schemas generated: {', '.join(schemas.keys())}")
    
    md_file = output_dir / "CONFIG_SCHEMA.md"
    with open(md_file, "w") as f:
        f.write("# Configuration Schema\n\n")
        f.write("Auto-generated from Pydantic models.\n\n")
        
        for name, schema in schemas.items():
            f.write(f"## {name}\n\n")
            if "description" in schema:
                f.write(f"{schema['description']}\n\n")
            
            if "properties" in schema:
                f.write("### Properties\n\n")
                for prop, details in schema["properties"].items():
                    prop_type = details.get("type", "any")
                    prop_desc = details.get("description", "")
                    default = details.get("default", "")
                    
                    f.write(f"- **{prop}** (`{prop_type}`)")
                    if default:
                        f.write(f" - Default: `{default}`")
                    f.write("\n")
                    if prop_desc:
                        f.write(f"  {prop_desc}\n")
                    f.write("\n")
            
            f.write("\n")
    
    print(f"📝 Generated markdown docs: {md_file}")
    return len(schemas)
