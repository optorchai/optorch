"""identity queries registration"""

from optorch.storage.queries.registry import QueryRegistry


def register_identity_queries(registry: QueryRegistry, backend: str = "sqlite"):
    """register all identity queries for given backend"""
    import importlib
    
    query_names = [
        "create_organization",
        "get_organization",
        "update_organization",
        "delete_organization",
        "list_organizations",
        "find_organizations_by_parent",
        "create_individual",
        "get_individual",
        "get_individual_by_email",
        "update_individual",
        "update_individual_password",
        "delete_individual",
        "list_individuals",
        "list_individuals_filtered",
        "add_membership",
        "create_membership",
        "get_membership",
        "update_membership_status",
        "delete_membership",
        "list_memberships",
        "get_org_members",
        "list_roles",
        "create_scim_token",
        "get_scim_token",
        "delete_scim_token",
        "create_invite_token",
        "get_invite_token",
        "invalidate_invite_token",
        "create_reset_token",
        "get_reset_token",
        "invalidate_reset_token",
        "create_session",
        "delete_session",
        "revoke_refresh_token",
        "check_revoked_token",
        "get_jwt_keys",
        "save_jwt_key",
        "delete_expired_jwt_keys",
        "list_casbin_policies",
        "save_casbin_policy",
        "delete_casbin_policy",
        "clear_casbin_policies",
        "create_audit_log",
    ]
    
    for query_name in query_names:
        module_path = f"optorch.identity.queries.{query_name}.{backend}"
        try:
            module = importlib.import_module(module_path)
            class_name = "".join(word.capitalize() for word in query_name.split("_")) + "Query"
            query_class = getattr(module, class_name)
            registry.register(backend, f"identity.{query_name}", query_class)
        except (ImportError, AttributeError) as e:
            from optorch.logging import get_logger
            logger = get_logger(__name__)
            logger.warning(f"failed to register identity query {query_name} for {backend}: {e}")
