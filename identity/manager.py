"""identity manager - unified facade for all identity subsystems"""

from typing import Any, Optional, List, TYPE_CHECKING
from optorch.identity.config import IdentityConfig
from optorch.identity.context import IdentityContext
from optorch.logging import get_logger

if TYPE_CHECKING:
    from optorch.storage.manager import StorageManager
    from optorch.events.event_emitter import EventEmitter
    from optorch.identity.organization.models import Individual
    from optorch.cache.manager import CacheManager
    from optorch.config.secrets.provider import SecretProvider
    from optorch.identity.licensing.manager import LicenseManager
    from optorch.identity.organization.manager import OrganizationManager
    from optorch.identity.authentication.manager import AuthenticationManager
    from optorch.identity.provisioning.manager import SCIMManager
    from optorch.identity.authorization.manager import AuthorizationManager
    from optorch.identity.protection.manager import ProtectionManager

logger = get_logger(__name__)


class IdentityManager:
    """unified identity facade - coordinates authentication, authorization, organization, licensing"""

    authn: "AuthenticationManager"
    org: "OrganizationManager"
    license: "LicenseManager"
    provisioning: "SCIMManager"
    authz: "AuthorizationManager"
    protection: "ProtectionManager"

    def __init__(
        self,
        config: IdentityConfig,
        storage_manager: Optional["StorageManager"] = None,
        event_emitter: Optional["EventEmitter"] = None,
        cache_manager: Optional["CacheManager"] = None,
        secrets_provider: Optional["SecretProvider"] = None,
        notification_manager: Optional[Any] = None,
        constraint_registry: Optional[Any] = None,
    ):
        """initialize identity manager

        Args:
            config: identity configuration (includes storage settings)
            storage_manager: optional shared storage (hobby mode). If not provided, creates new connection
            event_emitter: for emitting identity events (optional)
            cache_manager: for token blacklisting, policy caching (optional)
            secrets_provider: for on-demand secret fetching (optional - for OIDC/SAML providers)
            notification_manager: for email verification (optional)
            constraint_registry: ABAC constraint registry for fine-grained access control (optional)
        """
        self.config = config
        self.event_emitter = event_emitter
        self.cache_manager = cache_manager
        self.secrets_provider = secrets_provider
        self._notification_manager = notification_manager
        self.constraint_registry = constraint_registry
        self.context = IdentityContext()

        if storage_manager:
            self.storage = storage_manager
            logger.debug("identity using shared storage manager")
        elif hasattr(config, "storage") and config.storage and config.storage.connection_string:
            from optorch.storage.manager import StorageManager

            config.storage.migrations_enabled = False
            self.storage = StorageManager(config=config.storage)
            logger.debug(f"identity storage initialized: {config.storage.connection_string}")
        else:
            from optorch.storage.manager import StorageManager
            from optorch.storage.config import StorageConfig
            import os

            sqlite_path = os.path.join(os.getcwd(), "data", "identity.db")
            os.makedirs(os.path.dirname(sqlite_path), exist_ok=True)

            sqlite_config = StorageConfig(
                store="sqlite",
                connection_string=f"sqlite:///{sqlite_path}",
                migrations_enabled=False
            )
            self.storage = StorageManager(config=sqlite_config)

            logger.info(f"identity storage defaulted to SQLite: {sqlite_path}")

        # register identity migrations
        # - shared storage: migrations run during initialize_async()
        # - dedicated storage: migrations run on first query (lazy)
        import os
        migrations_path = os.path.join(os.path.dirname(__file__), "migrations")
        self.storage.add_migrations("identity", migrations_path)
        
        if storage_manager:
            logger.debug(f"identity using shared storage with migrations from {migrations_path}")
        else:
            logger.debug(f"identity using dedicated storage with migrations from {migrations_path} (lazy init)")

        self._register_queries()
        self._initialize_managers()

    def _register_queries(self) -> None:
        """register identity queries for current storage backend"""
        from optorch.identity.queries import register_identity_queries

        backend = self._detect_backend()
        register_identity_queries(self.storage.query_registry, backend)
        logger.debug(f"registered identity queries for {backend}")

    def _detect_backend(self) -> str:
        """detect storage backend type"""
        if hasattr(self.storage, "store") and self.storage.store:
            return self.storage.store.store_type

        conn_str = getattr(self.storage, "connection_string", "")
        if "postgresql" in conn_str or "postgres" in conn_str:
            return "timescale"
        elif "mysql" in conn_str:
            return "mysql"
        return "sqlite"

    def _initialize_managers(self) -> None:
        """initialize child managers using provider registries"""
        from optorch.identity.authentication.registry import AuthenticationProviderRegistry
        from optorch.identity.authorization.registry import AuthorizationProviderRegistry
        from optorch.identity.authentication.manager import AuthenticationManager
        from optorch.identity.authorization.manager import AuthorizationManager
        from optorch.identity.organization.manager import OrganizationManager
        from optorch.identity.licensing.manager import LicenseManager
        from optorch.identity.provisioning.manager import SCIMManager
        from optorch.identity.protection.manager import ProtectionManager
        from optorch.identity.protection.registry import ProtectionRegistry
        from optorch.identity.protection.enforcement import EnforcementRegistry

        authn_registry = AuthenticationProviderRegistry()
        authz_registry = AuthorizationProviderRegistry()

        authn_providers = authn_registry.create_providers_from_config(
            config=self.config.authentication,
            storage_manager=self.storage,
            cache_manager=self.cache_manager,
            secrets_manager=self.secrets_provider,
            notification_manager=getattr(self, "_notification_manager", None),
        )

        authz_provider = authz_registry.create_provider_from_config(
            config=self.config.authorization,
            storage_manager=self.storage,
            constraint_registry=self.constraint_registry,
        )

        self.authn = AuthenticationManager(
            providers=authn_providers,
            storage_manager=self.storage,
            event_emitter=self.event_emitter,
            cache_manager=self.cache_manager,
            secrets_provider=self.secrets_provider,
            enable_audit_logging=self.config.audit.enable_audit_logging,
            enable_rate_limiting=self.config.authentication.enable_rate_limiting,
        )

        self.authz = AuthorizationManager(
            provider=authz_provider, 
            event_emitter=self.event_emitter,
            storage_manager=self.storage,
            enable_audit_logging=self.config.audit.enable_audit_logging
        )
        self.org = OrganizationManager(storage=self.storage, event_emitter=self.event_emitter)
        self.license = LicenseManager(
            config=self.config.licensing,
            org_manager=self.org,
            event_emitter=self.event_emitter,
            storage_manager=self.storage
        )
        self.provisioning = SCIMManager(config=self.config.provisioning, org_manager=self.org, event_emitter=self.event_emitter)

        protection_registry = ProtectionRegistry()
        enforcement_registry = EnforcementRegistry()
        self.protection = ProtectionManager(identity=self, registry=protection_registry, enforcement=enforcement_registry)

        self._initialize_webhooks()

        logger.info("identity manager initialized")

    def _initialize_webhooks(self) -> None:
        """initialize webhook registry and event listener"""
        if not self.config.webhooks.enabled:
            logger.debug("webhooks disabled in config")
            self.webhook_registry = None
            return
        
        if not self.event_emitter:
            logger.warning("webhooks enabled but no event_emitter - skipping webhook initialization")
            self.webhook_registry = None
            return
        
        from optorch.identity.webhooks import WebhookRegistry, WebhookEventListener
        
        self.webhook_registry = WebhookRegistry()
        self.webhook_registry.max_retries = self.config.webhooks.max_retries
        self.webhook_registry.retry_backoff = self.config.webhooks.retry_backoff
        
        for event_type, subscriptions in self.config.webhooks.subscriptions.items():
            for sub in subscriptions:
                url = sub.get("url")
                if not url:
                    logger.warning(f"skipping webhook subscription for {event_type}: missing url")
                    continue
                
                self.webhook_registry.register(
                    event_type=event_type,
                    url=url,
                    headers=sub.get("headers", {})
                )
        
        self.webhook_listener = WebhookEventListener(self.webhook_registry)
        self.webhook_listener.register_with_emitter(self.event_emitter)
        
        logger.info(f"webhook system initialized: {len(self.config.webhooks.subscriptions)} event types configured")

    async def authenticate(self, request: Any) -> dict:
        """authenticate user from HTTP request
        
        Args:
            request: HTTP request object
            
        Returns:
            User dict with profile data
        """        
        auth_result = await self.authn.authenticate(request)
        
        if not auth_result.success:
            raise PermissionError(f"Authentication failed: {auth_result.error}")
        
        individual = auth_result.individual
        if not individual:
            raise PermissionError("Authentication succeeded but no individual returned")
        
        user = {
            "id": individual.id,
            "email": individual.email if hasattr(individual, "email") else individual.id,
            "name": f"{individual.given_name} {individual.family_name}",
            "current_org_id": getattr(individual, "current_org_id", None),
            "roles": getattr(individual, "roles", []),
            "entitlements": []
        }
        
        self.context.set_current_user(user)
        return user

    async def check_permission(
        self, resource: str, action: str, user: Optional[dict] = None
    ) -> bool:
        """check if user can perform action on resource

        Args:
            resource: resource type
            action: action to perform
            user: user dict (optional - uses context if not provided)

        Returns:
            True if permitted
        """
        if user is None:
            user = self.context.get_current_user()
            if not user:
                return False

        authz_result = await self.authz.check_permission(
            subject={"id": user["id"], "roles": user.get("roles", [])},
            resource={"type": resource},
            action=action,
            environment={"org_id": user.get("current_org_id")},
        )

        if not authz_result.permit:
            return False

        licensed_features = ["workflow", "chatbot", "analytics", "white_label"]
        if resource in licensed_features and user.get("current_org_id"):
            org = await self.org.get(user["current_org_id"])
            if org and org.license:
                license_result = await self.license.validate(
                    org.license, action=action, context={"feature": resource}
                )
                return license_result.permit
            return False

        return True

    async def require_permission(
        self, resource: str, action: str, user: Optional[dict] = None
    ) -> None:
        """require permission - raises if denied

        Args:
            resource: resource type
            action: action to perform
            user: user dict (optional - uses context if not provided)

        Raises:
            PermissionError: permission denied
        """
        if not await self.check_permission(resource, action, user):
            raise PermissionError(f"Permission denied: {action} on {resource}")

    async def switch_organization(self, org_id: int, user: Optional[dict] = None) -> dict:
        """switch user's active organization
        
        Args:
            org_id: target organization ID
            user: user dict (optional - uses current user from context)
            
        Returns:
            Updated user dict with new org context
            
        Raises:
            PermissionError: user not permitted or not a member
        """
        if user is None:
            user = self.context.get_current_user()
            if not user:
                raise PermissionError("No user in context")
        
        await self.require_permission(resource="organization", action="switch", user=user)
        
        membership = await self.org.get_membership(user["id"], org_id)
        if not membership:
            raise PermissionError(f"User {user['id']} not member of {org_id}")
        
        user["current_org_id"] = org_id
        user["roles"] = membership.roles
        
        org = await self.org.get(org_id)
        if org and org.license:
            user["entitlements"] = self.license.extract_entitlements(org.license)
        
        self.context.set_current_user(user)
        return user
    
    async def get_group_members(self, group_id: int) -> List['Individual']:
        """get all members of a group (organization)
        
        Args:
            group_id: organization/group ID
            
        Returns:
            List of Individual objects who are members
        """
        memberships = await self.org.get_org_members(group_id)
        members = []
        
        for membership in memberships:
            individual = await self.org.get_individual(membership.user_id)
            if individual:
                members.append(individual)
        
        return members
    
    async def initialize_async(self) -> None:
        """explicitly initialize storage and run migrations
        
        call this if you need migrations to run before first identity operation.
        otherwise migrations run lazily on first query.
        
        note: shared storage (hobby mode) always runs migrations during app initialize_async()
        """
        await self.storage._ensure_initialized()
        logger.info("identity storage initialized and migrations complete")
