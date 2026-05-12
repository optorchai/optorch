"""identity package initializer - container integration"""

from typing import TYPE_CHECKING, Dict, Any, Optional
from optorch.logging import get_logger

if TYPE_CHECKING:
    from optorch.container import ApplicationContainer
    from optorch.config.manager import ConfigManager
    from optorch.identity.manager import IdentityManager
    from optorch.storage.manager import StorageManager
    from optorch.identity.authorization.constraints.registry import ConstraintRegistry

logger = get_logger(__name__)


class IdentityPackageInitializer:
    """self-contained identity system initialization"""

    @staticmethod
    def initialize(
        config_manager: "ConfigManager",
        container: Optional["ApplicationContainer"] = None,
        config: Optional[Dict[str, Any]] = None,
        overrides: Optional[Dict[str, Any]] = None,
    ) -> Optional["IdentityManager"]:
        """initialize identity system and attach to container

        Args:
            config_manager: ConfigManager instance
            container: ApplicationContainer to attach to
            config: optional optorch config dict override
            overrides: optional dict overrides

        Returns:
            IdentityManager instance or None
        """
        from optorch.identity.manager import IdentityManager
        from optorch.identity.config import IdentityConfig

        if not container:
            logger.warning("no container provided - identity not initialized")
            return None

        if hasattr(container, "identity") and container.identity:
            logger.debug("identity already initialized - skipping")
            return container.identity

        config_manager.register_config("identity", IdentityConfig)
        logger.info("✅ identity config model registered")

        identity_config_dict = config_manager.get("identity", {})
        identity_config = IdentityConfig(**identity_config_dict)
        constraint_registry = IdentityPackageInitializer._initialize_constraint_registry(config_manager)

        shared_storage = None
        if identity_config.storage and hasattr(identity_config.storage, "share_container_storage") and identity_config.storage.share_container_storage:  # type: ignore[attr-defined]
            shared_storage = getattr(container, "storage_manager", None)
            if shared_storage:
                logger.debug("identity will use shared container storage")
            else:
                logger.warning(
                    "share_container_storage=true but no container.storage_manager available"
                )

        identity = IdentityManager(
            config=identity_config,
            storage_manager=shared_storage,
            event_emitter=getattr(container, "event_emitter", None),
            cache_manager=getattr(container, "cache_manager", None),
            secrets_provider=getattr(container.config_manager, "secret_provider", None) if hasattr(container, "config_manager") else None,
            notification_manager=getattr(container, "notification_manager", None),
            constraint_registry=constraint_registry,
        )

        container.identity = identity
        logger.info("✅ IdentityManager initialized")

        IdentityPackageInitializer._load_protections(config_manager, identity)
        IdentityPackageInitializer._register_authorization_intent(config_manager, container)

        return identity

    @staticmethod
    def _initialize_constraint_registry(
        config_manager: "ConfigManager"
    ) -> "ConstraintRegistry":
        """initialize constraint registry for ABAC
        
        builtins auto-register, this allows custom constraints from config
        
        Returns:
            ConstraintRegistry instance
        """
        from optorch.identity.authorization.constraints import ConstraintRegistry
        
        registry = ConstraintRegistry()  # builtins auto-register
        logger.debug(f"constraint registry initialized with: {registry.list_providers()}")
        
        constraints_config = config_manager.get("constraints", {})
        if constraints_config:
            custom_constraints = constraints_config.get("custom", {})
            for name, config in custom_constraints.items():
                if not config.get("enabled", True):
                    continue
                    
                class_name = config.get("class")
                if not class_name:
                    logger.warning(f"constraint {name} missing class name")
                    continue
                    
                try:
                    module_path, class_name_part = class_name.rsplit(".", 1)
                    module = __import__(module_path, fromlist=[class_name_part])
                    constraint_class = getattr(module, class_name_part)
                    registry.register(name, constraint_class)
                    logger.info(f"✅ registered custom constraint: {name}")
                except Exception as e:
                    logger.error(f"failed to register constraint {name}: {e}")
        
        return registry

    @staticmethod
    def _load_protections(
        config_manager: "ConfigManager", identity: "IdentityManager"
    ) -> None:
        """load protection rules from config/protections.yaml
        
        Args:
            config_manager: config manager
            identity: identity manager instance
        """
        protections_config = config_manager.get("protections", {})
        if protections_config:
            protections_dict = protections_config.get("protections", {})
            if protections_dict:
                identity.protection.registry.load_from_config(protections_dict)
                logger.info(
                    f"✅ loaded protections for {len(protections_dict)} resource types"
                )
            else:
                logger.debug("no protections.protections key found in config")
        else:
            logger.debug("no protections config found - protection registry empty")

    @staticmethod
    def _register_authorization_intent(
        config_manager: "ConfigManager", 
        container: "ApplicationContainer"
    ) -> None:
        """register authorization intent for node-level access control
        
        Args:
            config_manager: config manager instance
            container: application container
        """
        from optorch.identity.authorization.adapters import register_authorization_intent
        
        authz_config = config_manager.get("authorization", {})
        intent_config = authz_config.get("intent", {})
        
        enabled = intent_config.get("enabled", False)
        if not enabled:
            logger.debug("authorization intent disabled in config")
            return
        
        default_enforcement = intent_config.get("default_enforcement", "block")
        default_risk_level = intent_config.get("default_risk_level", "medium")
        
        try:
            register_authorization_intent(
                container=container,
                enabled=True,
                default_enforcement=default_enforcement,
                default_risk_level=default_risk_level
            )
        except Exception as e:
            logger.warning(f"failed to register authorization intent: {e}", exc_info=True)

    @staticmethod
    async def initialize_async(container: "ApplicationContainer") -> None:
        """async identity initialization - database migrations"""

        if not container or not hasattr(container, "identity") or not container.identity:
            logger.debug("no identity - async init skipped")
            return

        identity = container.identity

        if identity.storage:
            is_shared = identity.storage is getattr(container, "storage_manager", None)

            if is_shared:
                logger.debug("identity using shared storage - migrations handled by container")
            else:
                logger.info("running identity migrations on isolated storage")
                await IdentityPackageInitializer._run_migrations(identity.storage)
        else:
            logger.debug("no identity storage - migrations skipped")

        await identity.org.initialize()
        await identity.license.initialize()
        
        await IdentityPackageInitializer._bootstrap_default_user(container)

        logger.info("✅ identity async init complete")

    @staticmethod
    async def _run_migrations(storage_manager: Optional["StorageManager"]):
        """run identity system database migrations

        Args:
            storage_manager: storage instance to run migrations against
        """

        if not storage_manager:
            logger.warning("no storage_manager - migrations skipped")
            return
        
        await storage_manager._ensure_initialized()
        logger.info("✅ identity migrations complete")
    
    @staticmethod
    async def _bootstrap_default_user(container: "ApplicationContainer") -> None:
        """create default user/org on first boot if configured"""
        if not container or not container.identity:
            return
        
        identity = container.identity
        config_manager = container.config_manager
        
        identity_config = config_manager.get("identity", {})
        bootstrap_config = identity_config.get("bootstrap", {})
        
        if not bootstrap_config.get("create_default_user"):
            logger.debug("default user creation disabled")
            return
        
        user_config = bootstrap_config.get("default_user")
        if not user_config:
            logger.warning("create_default_user=true but no default_user config")
            return
        
        email = user_config.get("email")
        if not email:
            logger.warning("default_user missing email - skipping")
            return
        
        try:
            existing = await identity.storage.query("identity.get_individual_by_email", email=email)
            if existing:
                logger.debug(f"default user {email} already exists - skipping")
                return
        except Exception:
            pass  # user doesn't exist, continue
        
        password_key = user_config.get("password")
        if not password_key:
            logger.warning("default_user missing password - skipping")
            return
        
        password = config_manager.get_secret(password_key, "admin123")
        
        try:
            from optorch.identity.authentication.providers.builtin.user_manager import UserManager
            from optorch.identity.authentication.password.manager import PasswordManager
            from optorch.identity.authentication.password.config import PasswordManagerConfig
            
            password_mgr = PasswordManager(PasswordManagerConfig(provider="nist"))
            
            user_manager = UserManager(
                storage_manager=identity.storage,
                notification_manager=None,
                password_manager=password_mgr
            )
            
            org_id = "default-org"
            try:
                org = await identity.storage.query("identity.get_organization", organization_id=org_id)
                if not org:
                    await identity.storage.query(
                        "identity.create_organization",
                        organization_id=org_id,
                        name="Default Organization",
                        description="Auto-created default organization",
                        status="active"
                    )
                    logger.info(f"✅ created default organization: {org_id}")
            except Exception as org_err:
                logger.warning(f"could not verify/create organization: {org_err}")
            
            # create individual
            full_name = f"{user_config.get('given_name', 'Admin')} {user_config.get('family_name', 'User')}"
            individual = await user_manager.create_individual(
                email=email,
                name=full_name,
                organization_id=org_id,
                password=password,
                roles=["admin"],
                send_invite=False  # skip invite email for bootstrap
            )
            
            logger.info(f"✅ created default user: {email}")
            
        except Exception as e:
            logger.error(f"failed to create default user: {e}", exc_info=True)

    @staticmethod
    def discover(
        config_manager: "ConfigManager",
        container: "ApplicationContainer",
        force: bool = False,
    ) -> None:
        """discover custom authentication/authorization providers"""
        if not container or not container.identity:
            logger.warning("no identity - providers not discovered")
            return

        identity_config = config_manager.get("identity", {})
        if not force and not identity_config.get("auto_discover", True):
            logger.debug("identity auto_discover disabled")
            return

        logger.debug("identity provider discovery complete")
