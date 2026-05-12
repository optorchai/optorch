"""authorization decorators - pythonic permission checks

clean decorator API instead of manual check_permission calls
"""

from functools import wraps
from typing import Callable, Optional, List
from datetime import datetime, UTC
from optorch.errors import AuthorizationError


def require_permission(
    resource: str,
    action: str,
    resource_id_param: Optional[str] = None,
    extract_context: Optional[Callable] = None
):
    """decorator for permission-protected functions/endpoints
    
    Args:
        resource: Resource type ("workflow", "config", "node", etc.)
        action: Action type ("execute", "read", "update", "delete", etc.)
        resource_id_param: Optional parameter name containing resource ID
        extract_context: Optional function to extract environment context
    
    Usage:
        @require_permission("workflow", "execute", resource_id_param="workflow_id")
        async def execute_workflow(workflow_id: str, user: Individual):
            ...
        
        @require_permission("config", "write")
        async def update_config(key: str, value: str, user: Individual):
            ...
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # extract request and user from args/kwargs
            request = None
            user = None
            identity = None
            
            # check kwargs first
            if "request" in kwargs:
                request = kwargs["request"]
            if "user" in kwargs:
                user = kwargs["user"]
            
            # check args (look for Request and Individual types)
            for arg in args:
                if hasattr(arg, "app") and hasattr(arg, "state"):  # likely Request
                    request = arg
                elif hasattr(arg, "id") and hasattr(arg, "roles"):  # likely Individual
                    user = arg
            
            # get identity manager from request
            if request and hasattr(request.app, "state") and hasattr(request.app.state, "container"):
                identity = request.app.state.container.identity
            
            if not identity:
                raise AuthorizationError("Identity system not available", details={"resource": resource, "action": action})
            
            if not user:
                raise AuthorizationError("User not authenticated", details={"resource": resource, "action": action})
            
            # build resource dict
            resource_dict = {"type": resource}
            
            if resource_id_param and resource_id_param in kwargs:
                resource_dict["id"] = kwargs[resource_id_param]
            
            # extract environment context
            environment = {}
            if extract_context:
                environment = extract_context(request, user, kwargs)
            elif request:
                # default context extraction
                environment = {
                    "ip_address": request.client.host if request.client else None,
                    "user_agent": request.headers.get("user-agent"),
                    "org_id": user.current_org_id if hasattr(user, "current_org_id") else None
                }
            
            # check permission
            subject = {"user_id": user.id, "roles": user.roles if hasattr(user, "roles") else []}
            if hasattr(user, "current_org_id"):
                subject["org_id"] = user.current_org_id
            
            decision = await identity.authorization.check_permission(
                subject=subject,
                resource=resource_dict,
                action=action,
                environment=environment
            )
            
            if not decision.permit:
                raise AuthorizationError(
                    f"Permission denied: {action} on {resource}",
                    details={
                        "user_id": user.id,
                        "resource": resource,
                        "action": action,
                        "reason": decision.reason
                    }
                )
            
            # permission granted - execute function
            return await func(*args, **kwargs)
        
        return wrapper
    return decorator


def require_role(role: str):
    """decorator requiring specific role
    
    Args:
        role: Required role name
    
    Usage:
        @require_role("admin")
        async def delete_all_data(user: Individual):
            ...
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            user = kwargs.get("user") or next((arg for arg in args if hasattr(arg, "roles")), None)
            
            if not user:
                raise AuthorizationError("User not authenticated")
            
            user_roles = user.roles if hasattr(user, "roles") else []
            
            if role not in user_roles:
                raise AuthorizationError(
                    f"Role {role} required",
                    details={"user_id": user.id, "required_role": role, "user_roles": user_roles}
                )
            
            return await func(*args, **kwargs)
        
        return wrapper
    return decorator


def require_any_role(roles: List[str]):
    """decorator requiring at least one of specified roles
    
    Args:
        roles: List of acceptable roles
    
    Usage:
        @require_any_role(["admin", "devops"])
        async def deploy_to_production(user: Individual):
            ...
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            user = kwargs.get("user") or next((arg for arg in args if hasattr(arg, "roles")), None)
            
            if not user:
                raise AuthorizationError("User not authenticated")
            
            user_roles = user.roles if hasattr(user, "roles") else []
            
            if not any(r in user_roles for r in roles):
                raise AuthorizationError(
                    f"One of roles {roles} required",
                    details={"user_id": user.id, "required_roles": roles, "user_roles": user_roles}
                )
            
            return await func(*args, **kwargs)
        
        return wrapper
    return decorator


def require_all_roles(roles: List[str]):
    """decorator requiring ALL specified roles
    
    Args:
        roles: List of required roles
    
    Usage:
        @require_all_roles(["analyst", "finance"])
        async def view_financial_analytics(user: Individual):
            ...
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            user = kwargs.get("user") or next((arg for arg in args if hasattr(arg, "roles")), None)
            
            if not user:
                raise AuthorizationError("User not authenticated")
            
            user_roles = user.roles if hasattr(user, "roles") else []
            
            if not all(r in user_roles for r in roles):
                raise AuthorizationError(
                    f"All roles {roles} required",
                    details={"user_id": user.id, "required_roles": roles, "user_roles": user_roles}
                )
            
            return await func(*args, **kwargs)
        
        return wrapper
    return decorator


def business_hours_only(start_hour: int = 9, end_hour: int = 17):
    """decorator restricting access to business hours
    
    Args:
        start_hour: Business hours start (0-23)
        end_hour: Business hours end (0-23)
    
    Usage:
        @business_hours_only(start_hour=8, end_hour=18)
        async def execute_batch_job(user: Individual):
            ...
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            now = datetime.now(UTC)
            if not (start_hour <= now.hour < end_hour):
                raise AuthorizationError(
                    f"Access restricted to business hours ({start_hour}:00-{end_hour}:00)",
                    details={"start_hour": start_hour, "end_hour": end_hour}
                )
            
            return await func(*args, **kwargs)
        
        return wrapper
    return decorator


def weekday_only():
    """decorator restricting access to weekdays only
    
    Usage:
        @weekday_only()
        async def run_production_deployment(user: Individual):
            ...
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            now = datetime.now(UTC)
            if now.weekday() >= 5:  # saturday=5, sunday=6
                raise AuthorizationError("Access restricted to weekdays (Monday-Friday)")
            
            return await func(*args, **kwargs)
        
        return wrapper
    return decorator


def require_same_org():
    """decorator ensuring subject and resource are in same organization
    
    Extracts org_id from user and resource_id parameter
    
    Usage:
        @require_same_org()
        async def edit_workflow(workflow_id: str, user: Individual, request: Request):
            ...
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            user = kwargs.get("user") or next((arg for arg in args if hasattr(arg, "current_org_id")), None)
            request = kwargs.get("request") or next((arg for arg in args if hasattr(arg, "app")), None)
            
            if not user:
                raise AuthorizationError("User not authenticated")
            
            user_org = user.current_org_id if hasattr(user, "current_org_id") else None
            
            # try to get resource org from state or kwargs
            resource_org = None
            if request and hasattr(request.state, "resource_org_id"):
                resource_org = request.state.resource_org_id
            
            # or extract from loaded resource in kwargs
            for key, value in kwargs.items():
                if isinstance(value, dict) and "org_id" in value:
                    resource_org = value["org_id"]
                    break
            
            if resource_org and user_org != resource_org:
                raise AuthorizationError(
                    "Cross-organization access denied",
                    details={"user_org": user_org, "resource_org": resource_org}
                )
            
            return await func(*args, **kwargs)
        
        return wrapper
    return decorator


def cost_limit(max_cost: float):
    """decorator enforcing cost limits on operations
    
    Args:
        max_cost: Maximum allowed cost
    
    Usage:
        @cost_limit(max_cost=100.0)
        async def execute_expensive_workflow(workflow_id: str, user: Individual):
            ...
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # look for cost in kwargs or request state
            estimated_cost = kwargs.get("estimated_cost", 0)
            
            request = kwargs.get("request") or next((arg for arg in args if hasattr(arg, "state")), None)
            if request and hasattr(request.state, "estimated_cost"):
                estimated_cost = request.state.estimated_cost
            
            if estimated_cost > max_cost:
                raise AuthorizationError(
                    f"Cost limit exceeded: ${estimated_cost:.2f} > ${max_cost:.2f}",
                    details={"estimated_cost": estimated_cost, "max_cost": max_cost}
                )
            
            return await func(*args, **kwargs)
        
        return wrapper
    return decorator
