"""Casbin authorization provider"""

from datetime import datetime, UTC
from pathlib import Path
from typing import TYPE_CHECKING, Optional, Any

from optorch.identity.authorization.provider import AuthorizationProvider
from optorch.identity.authorization.models import Decision
from optorch.errors import ConfigurationError
from optorch.logging import get_logger

if TYPE_CHECKING:
    from optorch.storage.manager import StorageManager
    from optorch.identity.authorization.constraints.registry import ConstraintRegistry
    from casbin.persist import Adapter as _BaseAdapter
else:
    try:
        from casbin.persist import Adapter as _BaseAdapter
    except ImportError:
        _BaseAdapter = object  # fallback when casbin not installed

logger = get_logger(__name__)


class StorageAdapter(_BaseAdapter):
    """Casbin adapter using optorch storage backend
    
    Stores policies in identity database using casbin_policies table.
    Supports both sync/async operations for Casbin compatibility.
    
    Inherits from casbin.persist.Adapter for Casbin isinstance validation.
    """
    
    def __init__(self, storage_manager: "StorageManager"):
        super().__init__()
        self.storage = storage_manager
        self._loop: Any = None
    
    def load_policy(self, model: Any) -> None:
        """Load all policies from storage (sync wrapper)"""
        import asyncio
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # already in event loop - just mark for loading
                logger.debug("deferring policy load - in event loop")
                return
            loop.run_until_complete(self._load_policy_async(model))
        except RuntimeError:
            # no event loop - policies will load on first enforcement
            logger.debug("no event loop for policy load - will load on demand")
    
    async def _load_policy_async(self, model: Any) -> None:
        """Load all policies from storage"""
        try:
            policies = await self.storage.query("identity.list_casbin_policies")
            
            for policy in policies:
                ptype = policy["ptype"]
                rule = policy["rule"]  # JSON array
                
                if ptype.startswith("p"):
                    sec = "p"
                    model.model["p"][ptype].policy.append(rule)
                elif ptype.startswith("g"):
                    sec = "g"
                    model.model["g"][ptype].policy.append(rule)
            
            logger.debug(f"loaded {len(policies)} casbin policies from storage")
        except Exception as e:
            logger.warning(f"failed to load casbin policies: {e}")
    
    def save_policy(self, model: Any) -> bool:
        """Save all policies to storage (sync wrapper)"""
        import asyncio
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # create task for async save
                asyncio.create_task(self._save_policy_async(model))
                return True
            return loop.run_until_complete(self._save_policy_async(model))
        except RuntimeError:
            logger.warning("cannot save policy - no event loop")
            return False
    
    async def _save_policy_async(self, model: Any) -> bool:
        """Save all policies to storage"""
        try:
            # clear existing policies
            await self.storage.query("identity.clear_casbin_policies")
            
            # save p policies
            for sec in ["p", "g"]:
                if sec in model.model:
                    for ptype, ast in model.model[sec].items():
                        for rule in ast.policy:
                            await self.storage.query(
                                "identity.save_casbin_policy",
                                ptype=ptype,
                                rule=rule
                            )
            
            logger.debug("saved casbin policies to storage")
            return True
        except Exception as e:
            logger.error(f"failed to save casbin policies: {e}")
            return False
    
    def add_policy(self, sec: str, ptype: str, rule: list[str]) -> bool:
        """Add a policy rule"""
        import asyncio
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.create_task(self._add_policy_async(ptype, rule))
                return True
            else:
                loop.run_until_complete(self._add_policy_async(ptype, rule))
                return True
        except RuntimeError:
            logger.warning("cannot add policy - no event loop")
            return False
    
    async def _add_policy_async(self, ptype: str, rule: list[str]) -> None:
        """Add a policy rule to storage"""
        await self.storage.query("identity.save_casbin_policy", ptype=ptype, rule=rule)
    
    def remove_policy(self, sec: str, ptype: str, rule: list[str]) -> bool:
        """Remove a policy rule"""
        import asyncio
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.create_task(self._remove_policy_async(ptype, rule))
                return True
            else:
                loop.run_until_complete(self._remove_policy_async(ptype, rule))
                return True
        except RuntimeError:
            logger.warning("cannot remove policy - no event loop")
            return False
    
    async def _remove_policy_async(self, ptype: str, rule: list[str]) -> None:
        """Remove a policy rule from storage"""
        await self.storage.query("identity.delete_casbin_policy", ptype=ptype, rule=rule)
    
    def remove_filtered_policy(self, sec: str, ptype: str, field_index: int, *field_values: str) -> bool:
        """Remove policies matching filter - not implemented for storage"""
        logger.warning("remove_filtered_policy not implemented for storage adapter")
        return False


class CasbinProvider(AuthorizationProvider):
    """Casbin authorization provider"""

    def __init__(
        self, 
        config: dict, 
        storage_manager: Optional["StorageManager"] = None, 
        constraint_registry: Optional["ConstraintRegistry"] = None
    ):
        try:
            import casbin as casbin_module
        except ImportError as e:
            raise ConfigurationError(
                "casbin not installed. Install with: pip install casbin",
                details={"import_error": str(e)}
            ) from e

        builtin_model = str(Path(__file__).parent / "rbac_model.conf")
        self.model_path = config.get("model_path") or builtin_model
        self.constraint_registry = constraint_registry
        self.storage = storage_manager
        
        # use storage adapter if available, otherwise memory mode
        if storage_manager:
            try:
                adapter = StorageAdapter(storage_manager)
                self.enforcer: Any = casbin_module.Enforcer(self.model_path, adapter)
                logger.info("casbin using storage backend")
            except Exception as e:
                logger.error(
                    f"failed to create casbin enforcer with storage: {type(e).__name__}: {str(e)}",
                    exc_info=True
                )
                raise
        else:
            self.enforcer: Any = casbin_module.Enforcer(self.model_path)
            logger.info("casbin using memory mode")
        
        # load static policies from config
        for policy in config.get("policies", []):
            ptype = policy.get("ptype", "p")
            if ptype == "p":
                self.enforcer.add_policy(*policy.get("rule", []))
            elif ptype == "g":
                self.enforcer.add_grouping_policy(*policy.get("rule", []))

    async def check_permission(
        self,
        subject: dict,
        resource: dict,
        action: str,
        environment: dict | None = None,
    ) -> Decision:
        """Evaluate using Casbin enforcer"""
        user_id = subject.get("user_id")
        resource_id = f"{resource.get('type')}:{resource.get('id', '*')}"

        for role in subject.get("roles", []):
            if self.enforcer.enforce(role, resource_id, action):
                return Decision(result="Permit", reason=f"Role {role} permits {action} on {resource_id}",)

        if self.enforcer.enforce(user_id, resource_id, action):
            return Decision(result="Permit", reason=f"User {user_id} has direct permission")

        if environment:
            abac_result = self._evaluate_abac(subject, resource, action, environment)
            if abac_result:
                return Decision(result="Permit", reason="ABAC condition satisfied")

        return Decision(result="Deny", reason="No matching policy found")

    def _evaluate_abac(
        self, subject: dict, resource: dict, action: str, environment: dict
    ) -> bool:
        """ABAC evaluation using constraint registry"""
        if not self.constraint_registry:
            current_hour = environment.get("time", datetime.now()).hour
            if current_hour < 9 or current_hour > 17:
                return False

            if subject.get("org_id") != resource.get("org_id"):
                return False

            return True
        
        from optorch.identity.authorization.constraints.models import (ConstraintContext, SubjectContext, ResourceContext, EnvironmentContext)
        from optorch.identity.authorization.constraints.config import ConstraintConfig, TimeConstraintConfig, ResourceConstraintConfig
        
        context = ConstraintContext(
            subject=SubjectContext(user_id=subject.get("user_id", ""), org_id=subject.get("org_id"), roles=subject.get("roles", [])),
            resource=ResourceContext(resource_id=resource.get("id"), owner_id=resource.get("owner_id"), org_id=resource.get("org_id")),
            action=action,
            environment=EnvironmentContext(current_time=environment.get("time", datetime.now(UTC)), ip_address=environment.get("ip_address"))
        )
        
        constraints = [
            ConstraintConfig(type="time", time=TimeConstraintConfig(start_hour=9, end_hour=17)),
            ConstraintConfig(type="resource", resource=ResourceConstraintConfig(require_same_org=True))
        ]
        
        return self.constraint_registry.evaluate_all(constraints, context)

    async def add_policy(self, policy: dict) -> None:
        """Add policy to Casbin"""
        subject = policy["subject"]
        resource = policy["resource"]
        action = policy["action"]

        self.enforcer.add_policy(subject, resource, action)
        self.enforcer.save_policy()

    async def remove_policy(self, policy_id: str) -> None:
        """Remove policy"""
        parts = policy_id.split(":")
        self.enforcer.remove_policy(*parts)
        self.enforcer.save_policy()

    async def list_policies(self) -> list[dict]:
        """List all policies"""
        policies = []
        for policy in self.enforcer.get_policy():
            policies.append(
                {"subject": policy[0], "resource": policy[1], "action": policy[2]}
            )
        return policies

    async def list_roles(self) -> list[str]:
        """list all roles from database (roles are stored in org memberships)"""
        if self.storage:
            try:
                return await self.storage.query("identity.list_roles")
            except Exception as e:
                logger.warning(f"failed to query roles from database: {e}")
        
        roles = set()
        for policy in self.enforcer.get_policy():
            subject = policy[0]
            if not any(char in subject for char in ['@', '-', '|']):
                roles.add(subject)
        
        for grouping in self.enforcer.get_grouping_policy():
            if len(grouping) >= 2:
                roles.add(grouping[1])
        
        return sorted(list(roles)) if roles else []

    def name(self) -> str:
        return "casbin"
