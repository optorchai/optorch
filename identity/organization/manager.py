"""Organization management"""

from typing import List, Optional, TYPE_CHECKING
from optorch.identity.organization.models import Organization, Individual, OrganizationMembership, UpdateOrganizationData
from optorch.errors import AuthorizationError

if TYPE_CHECKING:
    from optorch.storage.manager import StorageManager
    from optorch.identity.licensing.models import License
    from optorch.events.event_emitter import EventEmitter


class LicenseError(AuthorizationError):
    """License-related authorization errors"""
    pass


class OrganizationManager:
    """Manages organization operations"""

    def __init__(self, storage: "StorageManager", event_emitter: Optional["EventEmitter"] = None):
        self.storage = storage
        self.event_emitter = event_emitter

    async def initialize(self) -> None:
        """async initialization - create indexes, etc"""
        pass

    async def create(self, org: Organization) -> Organization:
        """Create organization"""
        import json
        
        created_org = await self.storage.query(
            "identity.create_organization",
            name=org.name,
            href=org.href,
            organization_type=org.organization_type,
            status=org.status,
            parent_id=org.parent_organization_id,
            license=org.license.uid if org.license else None,
            contact=json.dumps([c.model_dump() for c in org.contact]) if org.contact else None,
            characteristic=json.dumps([c.model_dump() for c in org.characteristic]) if org.characteristic else None,
            metadata=org.metadata
        )
        
        if self.event_emitter:
            self.event_emitter.emit("organization.created", {
                "organization_id": created_org.id,
                "name": created_org.name,
                "parent_id": created_org.parent_organization_id
            })
        
        return created_org

    async def get(self, org_id: int) -> Optional[Organization]:
        """Get organization by ID"""
        return await self.storage.query("identity.get_organization", organization_id=org_id)

    async def find_by_parent(self, parent_id: int) -> List[Organization]:
        """Get child organizations"""
        return await self.storage.query("identity.find_organizations_by_parent", parent_id=parent_id)

    async def get_effective_license(self, org_id: int) -> "License":
        """
        Resolve actual license for an organization.
        Walks up hierarchy if license_inherited=true.
        """
        org = await self.get(org_id)
        if not org:
            raise LicenseError(f"Organization {org_id} not found")

        if org.license is not None and not org.license_inherited:
            return org.license

        if org.license_inherited and org.parent_organization_id:
            return await self.get_effective_license(org.parent_organization_id)

        raise LicenseError(f"Organization {org_id} has no license and no parent to inherit from")

    async def check_license_permission(
        self, org_id: int, resource: str, action: str
    ) -> bool:
        """Check if organization has permission via own or inherited license"""
        effective_license = await self.get_effective_license(org_id)

        for permission in effective_license.permissions:
            if (
                permission.target == f"feature:{resource}"
                and permission.action == action
            ):
                return True

        return False

    async def get_ancestors(self, org_id: int) -> List[Organization]:
        """Get all parent organizations (up the hierarchy)"""
        ancestors = []
        current_id: Optional[int] = org_id

        while current_id:
            org = await self.get(current_id)
            if org and org.parent_organization_id:
                parent = await self.get(org.parent_organization_id)
                if parent:
                    ancestors.append(parent)
                    current_id = parent.id
                else:
                    break
            else:
                break

        return ancestors

    async def get_descendants(self, org_id: int) -> List[Organization]:
        """Get all child organizations (down the hierarchy)"""
        descendants = []
        children = await self.find_by_parent(org_id)

        for child in children:
            descendants.append(child)
            if child.id is not None:
                descendants.extend(await self.get_descendants(child.id))

        return descendants

    async def get_root(self, org_id: int) -> Organization:
        """Get root organization (top of hierarchy)"""
        org = await self.get(org_id)
        if not org:
            raise LicenseError(f"Organization {org_id} not found")

        while org.parent_organization_id:
            parent = await self.get(org.parent_organization_id)
            if not parent:
                break
            org = parent

        return org  # no parent = root

    async def create_individual(self, individual: Individual):
        """Create individual"""
        await self.storage.query("identity.create_individual", individual=individual)
        
        if self.event_emitter:
            self.event_emitter.emit("individual.created", {
                "user_id": individual.id,
                "email": individual.email,
                "name": f"{individual.given_name} {individual.family_name}"
            })

    async def get_individual(self, user_id: str) -> Optional[Individual]:
        """Get individual by ID"""
        return await self.storage.query("identity.get_individual", user_id=user_id)

    async def add_membership(self, membership: OrganizationMembership):
        """Add organization membership"""
        await self.storage.query("identity.add_membership", membership=membership)
        
        if self.event_emitter:
            self.event_emitter.emit("membership.added", {
                "user_id": membership.user_id,
                "organization_id": membership.organization_id,
                "roles": membership.roles
            })

    async def get_membership(
        self, user_id: str, org_id: int
    ) -> Optional[OrganizationMembership]:
        """Get membership"""
        return await self.storage.query("identity.get_membership", user_id=user_id, org_id=org_id)

    async def get_org_members(self, org_id: int) -> List[OrganizationMembership]:
        """Get all members of organization"""
        return await self.storage.query("identity.get_org_members", org_id=org_id)

    async def list_memberships(self, individual_id: str) -> List[OrganizationMembership]:
        """List all memberships for user"""
        return await self.storage.query("identity.list_memberships", individual_id=individual_id)

    async def update_membership_status(self, user_id: str, org_id: int, status: str):
        """Update membership status"""
        await self.storage.query("identity.update_membership_status", user_id=user_id, org_id=org_id, status=status)
        
        if self.event_emitter:
            self.event_emitter.emit("membership.role_changed", {
                "user_id": user_id,
                "organization_id": org_id,
                "new_status": status
            })

    async def update(self, organization_id: int, updates: UpdateOrganizationData) -> Optional[Organization]:
        """Update organization fields"""
        import json
        
        data = updates.model_dump(exclude_unset=True)
        if not data:
            return await self.get(organization_id)
        
        params = {"org_id": organization_id}
        
        if "name" in data:
            params["name"] = data["name"]
        if "href" in data:
            params["href"] = data["href"]
        if "organization_type" in data:
            params["organization_type"] = data["organization_type"]
        if "status" in data:
            params["status"] = data["status"]
        if "parent_id" in data:
            params["parent_organization_id"] = data["parent_id"]
        if "contact" in data:
            params["contact"] = data["contact"]
        if "characteristic" in data:
            params["characteristic"] = data["characteristic"]
        if "metadata" in data:
            params["metadata"] = data["metadata"]
        
        await self.storage.query(
            "identity.update_organization",
            _identity_context=None,
            org_id=params["org_id"],
            name=params.get("name"),
            href=params.get("href"),
            organization_type=params.get("organization_type"),
            status=params.get("status"),
            parent_organization_id=params.get("parent_organization_id"),
            contact=params.get("contact"),
            characteristic=params.get("characteristic"),
            metadata=params.get("metadata")
        )
        
        if self.event_emitter:
            self.event_emitter.emit("organization.updated", {
                "organization_id": organization_id,
                "fields": list(data.keys())
            })
        
        return await self.get(organization_id)

    async def delete(self, organization_id: int) -> bool:
        """Soft delete organization by setting status to deleted"""
        await self.storage.query("identity.delete_organization", org_id=organization_id)
        
        if self.event_emitter:
            self.event_emitter.emit("organization.deleted", {
                "organization_id": organization_id
            })
        
        return True

    async def remove_member(self, organization_id: int, individual_id: str) -> bool:
        """Remove member from organization"""
        await self.storage.query("identity.delete_membership", user_id=individual_id, org_id=organization_id)
        
        if self.event_emitter:
            self.event_emitter.emit("membership.removed", {
                "user_id": individual_id,
                "organization_id": organization_id
            })
        
        return True
