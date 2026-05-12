"""tenant filtering middleware - automatic org_id injection for multi-tenancy

enforces tenant boundaries by injecting WHERE organization_id = ? into queries
"""

from typing import Dict, Any, Optional, Set
from pydantic import BaseModel, Field
from optorch.logging import get_logger
from optorch.errors import ValidationError

logger = get_logger(__name__)


class TenantFilterConfig(BaseModel):
    """config for tenant filtering behavior"""
    
    enabled: bool = True
    strict_mode: bool = True
    
    # include rows with NULL organization_id (global/shared data)
    # True: WHERE (organization_id = :org_id OR organization_id IS NULL)
    # False: WHERE organization_id = :org_id (strict tenant isolation)
    include_global_data: bool = False  # default to strict isolation
    
    # tables that dont need tenant filtering (handle their own or are global)
    excluded_tables: Set[str] = Field(default_factory=lambda: {
        "individuals",  # users exist across orgs
        "organizations",  # org table itself
        "migrations",
        "jwt_keys",
        "revoked_tokens",
        "sessions",  # session has no org column
        "optorch_config"  # config queries handle tenant logic themselves
    })
    
    # queries explicitly excluded from filtering (handle their own tenant logic)
    excluded_queries: Set[str] = Field(default_factory=lambda: {
        "identity.get_individual",
        "identity.get_individual_by_email",
        "identity.list_individuals",
        "identity.create_individual",
        "identity.get_organization",  # org queries handle their own filtering
        "identity.list_organizations",
        "identity.create_organization",
        "get_config",  # config queries handle tenant logic themselves
        "save_config",
        "list_configs",
        "get_config_timestamp"
    })
    
    # queries that should include global data even when include_global_data=False
    # useful for analytics, shared templates, public resources
    always_include_global: Set[str] = Field(default_factory=set)
    
    class Config:
        frozen = False  # allow runtime updates


from optorch.storage.config import _rebuild_storage_config
_rebuild_storage_config()


class TenantFilter:
    """injects organization_id into query params for tenant isolation
    
    reads org_id from ambient contextvars or explicit parameter
    priority: explicit org_id param > ambient context
    """
    
    def __init__(self, config: TenantFilterConfig):
        self.config = config
        self.logger = get_logger(__name__)
    
    def _should_filter(self, query_name: str, params: Dict[str, Any]) -> bool:
        """determine if query needs tenant filtering"""
        if not self.config.enabled:
            return False
        
        if query_name in self.config.excluded_queries:
            logger.debug(f"skipping tenant filter for excluded query: {query_name}")
            return False
        
        if "organization_id" in params or "org_id" in params:
            logger.debug(f"query {query_name} already has org_id, skipping injection")
            return False
        
        return True
    
    def inject(self, query_name: str, params: Dict[str, Any], org_id: Optional[str] = None) -> Dict[str, Any]:
        """inject organization_id into query params if needed
        
        reads org_id from: explicit param > ambient contextvars
        
        controls global data visibility via _include_global marker:
        - include_global_data=True: queries should use (org_id = :org_id OR org_id IS NULL)
        - include_global_data=False: queries should use (org_id = :org_id) - strict isolation
        - always_include_global: per-query override to include global data
        
        args:
            query_name: identity.list_audit_logs, identity.list_teams, etc
            params: original query params
            org_id: explicit organization_id (bypasses ambient context)
        
        returns:
            params with organization_id injected if applicable
        
        raises:
            ValidationError: if strict_mode enabled and no org_id available
        """
        if not self._should_filter(query_name, params):
            return params
        
        # get org_id: explicit param > ambient context
        if not org_id:
            from optorch.identity.context import IdentityContext
            org_id = IdentityContext.get_ambient_org_id()
        
        if not org_id:
            msg = f"tenant filter enabled but no org_id in context for query: {query_name}"
            if self.config.strict_mode:
                raise ValidationError(msg, details={"query_name": query_name, "params": params})
            self.logger.warning(msg)
            return params
        
        filtered_params = params.copy()
        filtered_params["organization_id"] = org_id
        
        # determine if global data should be included
        should_include_global = (self.config.include_global_data or query_name in self.config.always_include_global)
        
        if should_include_global:
            filtered_params["_include_global"] = True
        
        logger.debug(
            f"injected org_id={org_id} into {query_name} "
            f"(include_global={should_include_global})"
        )
        return filtered_params
    
    def validate_table(self, table_name: str, has_org_column: bool) -> None:
        """validate table has org column if not excluded
        
        use during migrations/schema validation
        
        args:
            table_name: database table name
            has_org_column: whether table has organization_id column
        
        raises:
            ValidationError: if table should have org column but doesn't
        """
        if table_name in self.config.excluded_tables:
            return
        
        if not has_org_column:
            raise ValidationError(
                f"table {table_name} missing organization_id column - "
                f"required for tenant isolation (exclude via config if intentional)",
                details={"table_name": table_name, "excluded_tables": list(self.config.excluded_tables)}
            )



