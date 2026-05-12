"""SCIM 2.0 models for provisioning"""

from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional, Literal
from datetime import datetime, UTC


class SCIMEmail(BaseModel):
    """SCIM email address"""
    value: str
    type: Optional[str] = None
    primary: bool = False


class SCIMName(BaseModel):
    """SCIM name components"""
    given_name: str = Field(alias="givenName")
    family_name: str = Field(alias="familyName")
    middle_name: Optional[str] = Field(None, alias="middleName")
    honorific_prefix: Optional[str] = Field(None, alias="honorificPrefix")
    honorific_suffix: Optional[str] = Field(None, alias="honorificSuffix")
    formatted: Optional[str] = None

    model_config = ConfigDict(populate_by_name=True)


class SCIMGroup(BaseModel):
    """SCIM group membership"""
    value: str
    display: str
    type: Optional[str] = None


class SCIMMeta(BaseModel):
    """SCIM resource metadata"""
    resource_type: str = Field(alias="resourceType")
    created: datetime
    last_modified: Optional[datetime] = Field(None, alias="lastModified")
    location: Optional[str] = None

    model_config = ConfigDict(populate_by_name=True)


class SCIMUser(BaseModel):
    """SCIM 2.0 User resource"""
    schemas: List[str] = ["urn:ietf:params:scim:schemas:core:2.0:User"]
    id: Optional[str] = None
    external_id: Optional[str] = Field(None, alias="externalId")
    user_name: str = Field(alias="userName")
    name: SCIMName
    display_name: Optional[str] = Field(None, alias="displayName")
    emails: List[SCIMEmail] = []
    active: bool = True
    groups: List[SCIMGroup] = []
    meta: Optional[SCIMMeta] = None

    model_config = ConfigDict(populate_by_name=True)


class SCIMGroupResource(BaseModel):
    """SCIM 2.0 Group resource"""
    schemas: List[str] = ["urn:ietf:params:scim:schemas:core:2.0:Group"]
    id: Optional[str] = None
    display_name: str = Field(alias="displayName")
    members: List[dict] = []
    meta: Optional[SCIMMeta] = None

    model_config = ConfigDict(populate_by_name=True)


class SCIMPatchOperation(BaseModel):
    """SCIM PATCH operation"""
    op: Literal["add", "remove", "replace"]
    path: Optional[str] = None
    value: Optional[dict | str | bool] = None


class SCIMPatchRequest(BaseModel):
    """SCIM PATCH request"""
    schemas: List[str] = ["urn:ietf:params:scim:api:messages:2.0:PatchOp"]
    operations: List[SCIMPatchOperation] = Field(alias="Operations")

    model_config = ConfigDict(populate_by_name=True)


class SCIMError(BaseModel):
    """SCIM error response"""
    schemas: List[str] = ["urn:ietf:params:scim:api:messages:2.0:Error"]
    status: str
    detail: Optional[str] = None
    scim_type: Optional[str] = Field(None, alias="scimType")

    model_config = ConfigDict(populate_by_name=True)
