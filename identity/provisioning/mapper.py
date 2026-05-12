"""Map SCIM models to TMF632 models"""

from typing import TYPE_CHECKING
import re

if TYPE_CHECKING:
    from optorch.identity.organization.models import (Individual, OrganizationMembership)

from optorch.identity.provisioning.config import RoleMappingConfig


class SCIMMapper:
    """Map SCIM models to TMF632 models with configurable role mapping
    
    SCIM doesnt define group-to-role mappings - fully config-driven
    """

    def __init__(self, role_mapping: RoleMappingConfig | None = None):
        """initialize mapper with role mapping config
        
        Args:
            role_mapping: role mapping config (uses Pydantic defaults if None)
        """
        role_config = role_mapping or RoleMappingConfig()
        
        self.exact_role_mapping = {k.lower(): v for k, v in role_config.exact_mappings.items()}
        self.pattern_role_mapping = [
            (re.compile(pattern, re.IGNORECASE), role)
            for pattern, role in role_config.pattern_mappings.items()
        ]
        self.default_role = role_config.default_role
        self.preserve_unmapped = role_config.preserve_unmapped_groups

    def scim_user_to_individual(
        self, scim_user: dict, organization_id: str
    ) -> tuple["Individual", "OrganizationMembership"]:
        """Convert SCIM User → TMF632 Individual + OrganizationMembership"""
        from optorch.identity.organization.models import (
            Individual,
            OrganizationMembership,
            ContactMedium,
        )

        user_id = scim_user["userName"]
        name = scim_user.get("name", {})
        given_name = name.get("givenName", "")
        family_name = name.get("familyName", "")
        emails = scim_user.get("emails", [])

        individual = Individual(
            id=user_id,
            given_name=given_name,
            family_name=family_name,
            contact=[
                ContactMedium(type="email", value=email["value"])
                for email in emails
                if email.get("primary")
            ],
            status="active",
        )

        roles = self._extract_roles(scim_user.get("groups", []))

        membership = OrganizationMembership(
            id=f"{user_id}:{organization_id}",
            user_id=user_id,
            organization_id=organization_id,
            roles=roles,
            primary=True,
            status="active",
        )

        return individual, membership

    def _extract_roles(self, scim_groups: list) -> list[str]:
        """Map SCIM groups → optorch roles with config-driven matching
        
        Tries:
        1. Exact match (case-insensitive)
        2. Pattern match (regex)
        3. Preserve unmapped or use default
        """
        roles = set()
        
        for group in scim_groups:
            group_name = group.get("display", "").strip().lower()
            if not group_name:
                continue
            
            # exact match
            if group_name in self.exact_role_mapping:
                roles.add(self.exact_role_mapping[group_name])
                continue
            
            # pattern match
            matched = False
            for pattern, role in self.pattern_role_mapping:
                if pattern.match(group_name):
                    roles.add(role)
                    matched = True
                    break
            
            if not matched:
                if self.preserve_unmapped:
                    # sanitize group name to valid role identifier
                    custom_role = group_name.replace(" ", "_").replace("-", "_")
                    roles.add(custom_role)
                else:
                    roles.add(self.default_role)
        
        return list(roles) if roles else [self.default_role]

    def scim_group_to_roles(self, scim_group: dict) -> list[str]:
        """Convert SCIM Group → optorch roles
        
        Args:
            scim_group: SCIM Group resource
            
        Returns:
            list of role names
        """
        group_name = scim_group.get("displayName", "").strip().lower()
        
        if not group_name:
            return [self.default_role]
        
        # exact match
        if group_name in self.exact_role_mapping:
            return [self.exact_role_mapping[group_name]]
        
        # pattern match
        for pattern, role in self.pattern_role_mapping:
            if pattern.match(group_name):
                return [role]
        
        # unmapped handling
        if self.preserve_unmapped:
            custom_role = group_name.replace(" ", "_").replace("-", "_")
            return [custom_role]
        
        return [self.default_role]
