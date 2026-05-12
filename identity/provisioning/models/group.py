"""SCIM 2.0 Group models"""

from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List

class SCIMGroupMember(BaseModel):
    """SCIM Group member reference"""
    value: str = Field(..., description="User ID")
    ref: Optional[str] = Field(None, alias="$ref", description="URI reference to user")
    type: str = Field(default="User", description="Member type")
    display: Optional[str] = Field(None, description="Display name")


class SCIMGroupMeta(BaseModel):
    """SCIM Group metadata"""
    resourceType: str = "Group"
    created: Optional[str] = None
    lastModified: Optional[str] = None
    location: Optional[str] = None


class SCIMGroup(BaseModel):
    """SCIM 2.0 Group resource"""
    model_config = ConfigDict(populate_by_name=True)
    
    schemas: List[str] = Field(default=["urn:ietf:params:scim:schemas:core:2.0:Group"])
    id: Optional[str] = None
    externalId: Optional[str] = None
    displayName: str = Field(..., description="Group display name")
    members: Optional[List[SCIMGroupMember]] = Field(default_factory=list)
    meta: Optional[SCIMGroupMeta] = None


class SCIMGroupListResponse(BaseModel):
    """SCIM Group list response"""
    schemas: List[str] = Field(default=["urn:ietf:params:scim:api:messages:2.0:ListResponse"])
    totalResults: int
    startIndex: int = 1
    itemsPerPage: int
    Resources: List[SCIMGroup]
