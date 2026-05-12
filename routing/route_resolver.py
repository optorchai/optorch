from typing import Any
from .routing_context import RoutingContext
from .route_types import RouteTypes, RouteKeys
from optorch.state import State


class RouteResolver:
    @staticmethod
    def resolve(routing_config: dict[str, Any], context: RoutingContext) -> str | None:
        if not routing_config:
            return None
        
        if context.return_to:
            return context.return_to
        
        route_type = routing_config.get(RouteKeys.TYPE, RouteTypes.STATIC)
        
        if route_type == RouteTypes.END:
            return None
        
        elif route_type == RouteTypes.STATIC:
            return routing_config.get(RouteKeys.NEXT)
        
        elif route_type == RouteTypes.CONDITIONAL:
            on_field = routing_config.get(RouteKeys.ON)
            if not on_field:
                return routing_config.get(RouteKeys.DEFAULT)
            
            value = context.result.get(on_field)
            conditions = routing_config.get(RouteKeys.CONDITIONS, {})
            
            if value in conditions:
                return conditions[value]
            
            return routing_config.get(RouteKeys.DEFAULT)
        
        elif route_type == RouteTypes.DYNAMIC:
            conditions = routing_config.get(RouteKeys.CONDITIONS, [])
            for condition in conditions:
                if RouteResolver._evaluate_condition(condition[RouteKeys.IF], context.result):
                    return condition[RouteKeys.THEN]
            
            return routing_config.get(RouteKeys.DEFAULT)
        
        return routing_config.get(RouteKeys.DEFAULT)
    
    @staticmethod
    def _evaluate_condition(condition: str, state: State) -> bool:
        try:
            # Provide both 'state' and 'result' (dict) for backward compatibility
            namespace = {
                "state": state,
                "result": state.to_dict()
            }
            return eval(condition, {"__builtins__": {}}, namespace)
        except Exception:
            return False
