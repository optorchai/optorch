"""maps node configs to db for graph visualization"""
import json
from optorch.logging import get_logger
from typing import Any, TYPE_CHECKING
from pathlib import Path
import ast

from optorch.constants import NodeAttributes

if TYPE_CHECKING:
    from optorch.storage.manager import StorageManager

logger = get_logger(__name__)


class NodeGraphMapper:
    """maps node config + routing to db for analytics graph viz"""
    
    def __init__(self, storage_manager: 'StorageManager', nodes_config: dict[str, Any], entry_point: str | None = None):
        self.storage_manager = storage_manager
        self.nodes = nodes_config
        self.entry_point = entry_point
        self.base_package = "app.nodes"
        self.base_nodes_path = Path(self.base_package.replace(".", "/"))
    
    async def map_all_nodes(self) -> int:
        """
        map all nodes, enriching with:
        - phase detection from filesystem
        - routing introspection from Python AST
        - execution order calculation from routing chains
        """
        count = 0
        
        node_phases = self._discover_node_phases()
        node_routes = self._discover_node_routes()
        
        for node_name, node_config in self.nodes.items():
            if node_name in node_phases:
                node_config["phase"] = node_phases[node_name]
            
            if node_name in node_routes:
                routing = node_config.get("routing", {}) or {}
                if not isinstance(routing, dict):
                    routing = {}
                if "calls" not in routing:
                    routing["calls"] = []
                routing["calls"].extend(node_routes[node_name])
                node_config["routing"] = routing
        
        execution_orders, parent_maps = self._calculate_execution_order()
        
        for node_name, node_config in self.nodes.items():
            await self._map_node(
                node_name, 
                node_config,
                execution_order=execution_orders.get(node_name),
                parent_nodes=parent_maps.get(node_name, [])
            )
            count += 1
        
        logger.debug(f"node_graph_mapped count={count}")
        return count
    
    def _discover_node_phases(self) -> dict[str, str]:
        """scan app/nodes filesystem to detect which nodes are in phase subdirs"""
        phase_map = {}
        
        if not self.base_nodes_path.exists():
            return phase_map
        
        class_to_node = {}
        for node_name, config in self.nodes.items():
            class_name = config.get("class")
            if class_name:
                class_to_node[class_name] = node_name
        
        for item in self.base_nodes_path.iterdir():
            if item.is_dir() and (item / "__init__.py").exists():
                phase = item.name
                
                for node_file in item.iterdir():
                    if node_file.is_file() and node_file.suffix == ".py" and node_file.name != "__init__.py":
                        file_class_name = self._extract_class_name(node_file)
                        if file_class_name and file_class_name in class_to_node:
                            node_name = class_to_node[file_class_name]
                            phase_map[node_name] = phase
        
        return phase_map
    
    def _discover_node_routes(self) -> dict[str, list[str]]:
        """parse Python node files to find self.call() statements"""
        route_map = {}
        
        if not self.base_nodes_path.exists():
            return route_map
        
        class_to_node = {}
        for node_name, config in self.nodes.items():
            class_name = config.get("class")
            if class_name:
                class_to_node[class_name] = node_name
        
        for py_file in self.base_nodes_path.rglob("*.py"):
            if py_file.name == "__init__.py":
                continue
            
            file_class_name = self._extract_class_name(py_file)
            if file_class_name and file_class_name in class_to_node:
                node_name = class_to_node[file_class_name]
                routes = self._extract_routes_from_file(py_file)
                if routes:
                    route_map[node_name] = routes
        
        return route_map
    
    def _extract_routes_from_file(self, file_path: Path) -> list[str]:
        """
        extract possible routes from node file
        priority:
        1. __routes__ class attribute (explicit declaration)
        2. routing config (already passed in)
        3. AST parsing of self.call() (fallback for discovery)
        """
        routes = []
        
        try:
            with open(file_path) as f:
                content = f.read()
                tree = ast.parse(content, filename=str(file_path))
            
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    for item in node.body:
                        if isinstance(item, ast.Assign):
                            for target in item.targets:
                                if isinstance(target, ast.Name) and target.id == NodeAttributes.ROUTES:
                                    if isinstance(item.value, (ast.List, ast.Tuple)):
                                        for elt in item.value.elts:
                                            if isinstance(elt, ast.Constant):
                                                routes.append(elt.value)
                                    return routes
            
            calls_with_lineno = []
            for node in ast.walk(tree):
                if isinstance(node, ast.Call):
                    if isinstance(node.func, ast.Attribute):
                        if (isinstance(node.func.value, ast.Name) and 
                            node.func.value.id == "self" and 
                            node.func.attr == "call"):
                            if node.args and isinstance(node.args[0], ast.Constant):
                                target_node = node.args[0].value
                                if target_node:
                                    calls_with_lineno.append((node.lineno, target_node))
            
            calls_with_lineno.sort(key=lambda x: x[0])
            seen = set()
            for lineno, target in calls_with_lineno:
                if target not in seen:
                    routes.append(target)
                    seen.add(target)
            
            return routes
        except Exception as e:
            logger.warning(f"failed to parse {file_path}: {e}")
            return []
    
    def _extract_class_name(self, file_path: Path) -> str | None:
        """extract class name from Python file"""
        try:
            with open(file_path) as f:
                tree = ast.parse(f.read(), filename=str(file_path))
            
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    return node.name
            return None
        except Exception:
            return None
    
    async def _map_node(
        self, 
        node_name: str, 
        config: dict[str, Any],
        execution_order: int | None = None,
        parent_nodes: list[str] | None = None
    ) -> None:
        """map single node with full routing info to db"""
        
        routing = config.get("routing", {}) or {}
        default_route = routing.get("default")
        
        route_conditions = routing.get("conditions", [])
        route_calls = routing.get("calls", [])
        
        full_routing = {
            "conditions": route_conditions,
            "calls": route_calls
        }
        
        intents = config.get("intents", {})
        phase = config.get("phase")
        
        metadata = config.copy()
        
        await self.storage_manager.query(
            "save_node_config",
            node_name=node_name,
            phase=phase,
            domain=config.get("domain"),
            entity_type=config.get("entity_type"),
            class_name=config.get("class"),
            default_route=default_route,
            route_conditions=full_routing if (route_conditions or route_calls) else None,
            tools=config.get("tools", []),
            llm_model=config.get("llm"),
            streaming=config.get("streaming", False),
            prompts=config.get("prompts", {}),
            intents=intents,
            metadata=metadata,
            execution_order=execution_order,
            parent_nodes=parent_nodes if parent_nodes else None
        )
        
        logger.debug(f"node_mapped node={node_name}")
    
    def _calculate_execution_order(self) -> tuple[dict[str, int], dict[str, list[str]]]:
        """
        simulate router execution starting from entry_point to build parent relationships.
        tracks execution order and which nodes can route to which.
        for unreached nodes, still track parent_nodes from static config.
        returns: (execution_order_dict, parent_maps)
        """
        if not self.entry_point or self.entry_point not in self.nodes:
            logger.warning("No valid entry point - parent_nodes only from static config")
            return self._build_static_parent_map()
        
        parent_map: dict[str, list[str]] = {}
        execution_order: dict[str, int] = {}
        visited: set[str] = set()
        queue: list[tuple[str, int, str | None]] = [(self.entry_point, 0, None)]  # (node, order, parent)
        
        while queue:
            current_node, order, parent = queue.pop(0)
            
            if current_node not in self.nodes:
                continue
            
            if parent:
                if current_node not in parent_map:
                    parent_map[current_node] = []
                if parent not in parent_map[current_node]:
                    parent_map[current_node].append(parent)
            
            if current_node not in execution_order:
                execution_order[current_node] = order
            
            if current_node in visited:
                continue
            visited.add(current_node)
            
            routing = self.nodes[current_node].get("routing", {}) or {}
            
            for call in routing.get("calls", []):
                queue.append((call, order, current_node))
            
            if routing.get("default"):
                queue.append((routing["default"], order + 1, current_node))
            
            for cond in routing.get("conditions", []):
                if isinstance(cond, dict):
                    target = cond.get("then")
                    if target and not target.startswith("result.get"):
                        queue.append((target, order + 1, current_node))
        
        unreached = set(self.nodes.keys()) - visited
        if unreached:
            for node_name in unreached:
                routing = self.nodes[node_name].get("routing", {}) or {}
                
                for call in routing.get("calls", []):
                    if call not in parent_map:
                        parent_map[call] = []
                    if node_name not in parent_map[call]:
                        parent_map[call].append(node_name)
                
                if routing.get("default"):
                    target = routing["default"]
                    if target not in parent_map:
                        parent_map[target] = []
                    if node_name not in parent_map[target]:
                        parent_map[target].append(node_name)
                
                for cond in routing.get("conditions", []):
                    if isinstance(cond, dict):
                        target = cond.get("then")
                        if target and not target.startswith("result.get"):
                            if target not in parent_map:
                                parent_map[target] = []
                            if node_name not in parent_map[target]:
                                parent_map[target].append(node_name)
        
        logger.info(f"execution_simulation entry={self.entry_point} visited={len(visited)} unreached={len(unreached)} edges={sum(len(v) for v in parent_map.values())}")
        return execution_order, parent_map
    
    def _build_static_parent_map(self) -> tuple[dict[str, int], dict[str, list[str]]]:
        """fallback: build parent map from static routing config without simulation"""
        parent_map: dict[str, list[str]] = {}
        
        for node_name, config in self.nodes.items():
            routing = config.get("routing", {}) or {}
            
            for call in routing.get("calls", []):
                if call not in parent_map:
                    parent_map[call] = []
                if node_name not in parent_map[call]:
                    parent_map[call].append(node_name)
            
            if routing.get("default"):
                target = routing["default"]
                if target not in parent_map:
                    parent_map[target] = []
                if node_name not in parent_map[target]:
                    parent_map[target].append(node_name)
            
            for cond in routing.get("conditions", []):
                if isinstance(cond, dict):
                    target = cond.get("then")
                    if target and not target.startswith("result.get"):
                        if target not in parent_map:
                            parent_map[target] = []
                        if node_name not in parent_map[target]:
                            parent_map[target].append(node_name)
        
        return {}, parent_map
