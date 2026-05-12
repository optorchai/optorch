"""protection registry - policy information point (PIP) for resource metadata"""

from typing import Optional
from optorch.registry import Registry
from optorch.logging import get_logger
from optorch.identity.protection.config import ProtectionConfig

logger = get_logger(__name__)


class ProtectionRegistry(Registry[ProtectionConfig]):
    """registry of protected resources (UMA 2.0 Resource Registration pattern)
    
    maps resource identifiers to protection configs with enforcement strategies
    """

    def register(self, item: ProtectionConfig, key: Optional[str] = None) -> None:
        """override register to auto-generate key from protection config
        
        Args:
            item: protection config (first param for convenience)
            key: optional key override (auto-generated if not provided)
        """
        if key is None:
            key = f"{item.resource_type}:{item.resource_id}:{item.action}"
        super().register(key, item)

    def register_protection(
        self,
        resource_type: str,
        resource_id: str,
        action: str,
        permission: str,
        enforcement: str = "block",
        description: Optional[str] = None,
        ui_hint: Optional[str] = None,
        fallback: Optional[str] = None,
        interactive_approval: bool = False,
        approver_role: Optional[str] = None,
    ) -> None:
        """register protected resource with full config
        
        Args:
            resource_type: type of resource (config, tool, route, etc.)
            resource_id: identifier within that type
            action: action being protected (read, update, execute, etc.)
            permission: permission required (e.g., "config:secrets:update")
            enforcement: enforcement strategy (block|interactive|route|warn)
            description: human-readable description
            ui_hint: UI hint (e.g., "Admin only")
            fallback: fallback route for route enforcement
            interactive_approval: enable interactive approval flow
            approver_role: role required to approve
        """
        key = f"{resource_type}:{resource_id}:{action}"
        config = ProtectionConfig(
            resource_type=resource_type,
            resource_id=resource_id,
            action=action,
            permission=permission,
            enforcement=enforcement,
            description=description,
            ui_hint=ui_hint,
            fallback=fallback,
            interactive_approval=interactive_approval,
            approver_role=approver_role,
        )
        self.register(config, key)
        logger.debug(f"registered protection: {key} requires {permission} (enforcement: {enforcement})")

    def get_protection(
        self, resource_type: str, resource_id: str, action: str
    ) -> Optional[ProtectionConfig]:
        """get protection config for resource+action
        
        Args:
            resource_type: type of resource
            resource_id: identifier
            action: action being performed
        
        Returns:
            protection config or None if not protected
        """
        key = f"{resource_type}:{resource_id}:{action}"
        return self.get_optional(key)

    def is_protected(self, resource_type: str, resource_id: str, action: str) -> bool:
        """check if resource+action has protection rule
        
        Args:
            resource_type: type of resource
            resource_id: identifier
            action: action being performed
        
        Returns:
            True if protected
        """
        key = f"{resource_type}:{resource_id}:{action}"
        return self.has(key)

    def list_by_type(self, resource_type: str) -> list[ProtectionConfig]:
        """list all protections for resource type
        
        Args:
            resource_type: type to filter by
        
        Returns:
            list of protection configs
        """
        return [
            config
            for key, config in self._items.items()
            if config.resource_type == resource_type
        ]

    def load_from_config(self, protections_dict: dict) -> None:
        """load protections from config (YAML)
        
        Args:
            protections_dict: dict with resource types as keys, lists of protection rules as values
        
        Example:
            {
                "config": [
                    {
                        "resource_id": "optorch.llm.api_keys",
                        "action": "update",
                        "permission": "config:secrets:update",
                        "enforcement": "block"
                    }
                ],
                "tool": [...]
            }
        """
        count = 0
        for resource_type, rules in protections_dict.items():
            for rule in rules:
                self.register_protection(
                    resource_type=resource_type,
                    resource_id=rule["resource_id"],
                    action=rule["action"],
                    permission=rule["permission"],
                    enforcement=rule.get("enforcement", "block"),
                    description=rule.get("description"),
                    ui_hint=rule.get("ui_hint"),
                    fallback=rule.get("fallback"),
                    interactive_approval=rule.get("interactive_approval", False),
                    approver_role=rule.get("approver_role"),
                )
                count += 1
        logger.info(f"loaded {count} protection rules from config")
