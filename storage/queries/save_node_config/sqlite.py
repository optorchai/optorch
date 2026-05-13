from typing import Any, Dict, Optional, List
import json
from optorch.storage.queries.base import BaseQuery
from optorch.logging import get_logger

logger = get_logger(__name__)


class SaveNodeConfigQuery(BaseQuery):
    """save node configuration to node_registry - sqlite"""
    
    @property
    def query_name(self) -> str:
        return "save_node_config"
    
    async def execute(
        self,
        node_name: str,
        class_name: str,
        phase: Optional[str] = None,
        domain: Optional[str] = None,
        entity_type: Optional[str] = None,
        default_route: Optional[str] = None,
        route_conditions: Optional[Dict[str, Any]] = None,
        tools: Optional[List[str]] = None,
        llm_model: Optional[str] = None,
        streaming: bool = False,
        prompts: Optional[Dict[str, Any]] = None,
        intents: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        execution_order: Optional[int] = None,
        parent_nodes: Optional[List[str]] = None
    ) -> None:
        """upsert node config into node_registry table"""
        
        query = """
            INSERT OR REPLACE INTO node_registry (
                node_name, phase, domain, entity_type, class_name,
                default_route, route_conditions, tools, llm_model, streaming,
                prompts, intents, metadata, execution_order, parent_nodes
            ) VALUES (
                :node_name, :phase, :domain, :entity_type, :class_name,
                :default_route, :route_conditions, :tools, :llm_model, :streaming,
                :prompts, :intents, :metadata, :execution_order, :parent_nodes
            )
        """
        
        values = {
            "node_name": node_name,
            "phase": phase,
            "domain": domain,
            "entity_type": entity_type,
            "class_name": class_name,
            "default_route": default_route,
            "route_conditions": json.dumps(route_conditions) if route_conditions else None,
            "tools": json.dumps(tools) if tools else None,
            "llm_model": llm_model,
            "streaming": 1 if streaming else 0,
            "prompts": json.dumps(prompts) if prompts else None,
            "intents": json.dumps(intents) if intents else None,
            "metadata": json.dumps(metadata) if metadata else None,
            "execution_order": execution_order,
            "parent_nodes": json.dumps(parent_nodes) if parent_nodes else None
        }
        
        await self.store.execute(query, values)
        logger.debug(f"saved node config: {node_name}")
