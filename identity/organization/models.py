"""TMF632 Party Management models"""

from pydantic import BaseModel, Field
from datetime import datetime, UTC
from typing import Optional, List, Any, TYPE_CHECKING

if TYPE_CHECKING:
    from optorch.identity.licensing.models import License


class ContactMedium(BaseModel):
    """Contact information"""
    type: str  # "email" | "phone" | "address"
    value: str
    characteristic: dict = {}  # {"purpose": "billing"}


class OrganizationCharacteristic(BaseModel):
    """Custom attributes"""
    name: str
    value: Any


class UpdateOrganizationData(BaseModel):
    """Partial update data for organization"""
    name: Optional[str] = None
    href: Optional[str] = None
    organization_type: Optional[str] = None
    status: Optional[str] = None
    parent_id: Optional[int] = None
    contact: Optional[List[ContactMedium]] = None
    characteristic: Optional[List[OrganizationCharacteristic]] = None
    metadata: Optional[dict] = None


class Organization(BaseModel):
    """TMF632 Organization model"""
    id: Optional[int] = None
    name: str
    href: Optional[str] = None  # rest resource link
    organization_type: str = "Company"  # Company | Department | Team
    status: str = "active"  # active | inactive | suspended
    contact: List[ContactMedium] = []
    characteristic: List[OrganizationCharacteristic] = []
    parent_organization_id: Optional[int] = None
    license: Optional["License"] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    metadata: dict = {}

    @property
    def license_inherited(self) -> bool:
        """Check if organization inherits license from parent (TMF632 characteristic)"""
        for char in self.characteristic:
            if char.name == "license_inherited":
                return bool(char.value)
        return False


class Individual(BaseModel):
    """TMF632 Individual model"""
    id: str  # user id (email or uuid)
    given_name: str
    family_name: str
    email: str
    password_hash: Optional[str] = None
    href: Optional[str] = None
    middle_name: Optional[str] = None
    title: Optional[str] = None  # "Dr.", "Prof."
    status: str = "active"
    metadata: dict = {}
    last_login_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    deleted_at: Optional[datetime] = None


class OrganizationMembership(BaseModel):
    """User belongs to organization with roles"""
    id: str
    user_id: str
    organization_id: int
    roles: List[str] = []  # ["analyst", "node_executor"]
    primary: bool = False
    status: str = "active"
    valid_from: Optional[datetime] = None
    valid_until: Optional[datetime] = None
    joined_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class OrganizationParentRelationship(BaseModel):
    """Parent-child organization relationship"""
    id: str
    child: int
    parent: int
    relationship_type: str  # "reseller" | "department" | "subsidiary"
    characteristic: List[OrganizationCharacteristic] = []
    status: str = "active"
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


from optorch.identity.licensing.models import License
Organization.model_rebuild()
