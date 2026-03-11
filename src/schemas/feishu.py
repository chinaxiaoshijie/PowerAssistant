"""Pydantic schemas for Feishu API data validation.

These schemas validate incoming data from Feishu OpenAPI responses.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


class UserStatus(BaseModel):
    """User status information from Feishu API."""

    model_config = ConfigDict(populate_by_name=True)

    is_activated: bool = Field(default=True, alias="is_activated")
    is_frozen: bool = Field(default=False, alias="is_frozen")
    is_resigned: bool = Field(default=False, alias="is_resigned")
    is_unjoin: bool = Field(default=False, alias="is_unjoin")

    @property
    def is_active(self) -> bool:
        """Determine if user is active based on status fields."""
        return self.is_activated and not self.is_resigned and not self.is_unjoin


class FeishuAvatar(BaseModel):
    """Feishu user avatar information."""

    model_config = ConfigDict(populate_by_name=True)

    avatar_72: Optional[str] = Field(None, alias="avatar_72")
    avatar_240: Optional[str] = Field(None, alias="avatar_240")
    avatar_640: Optional[str] = Field(None, alias="avatar_640")
    avatar_origin: Optional[str] = Field(None, alias="avatar_origin")


class FeishuDepartmentRaw(BaseModel):
    """Raw department data from Feishu API.

    Schema for /contact/v3/departments response.
    """

    model_config = ConfigDict(populate_by_name=True)

    department_id: str = Field(..., alias="department_id")
    name: str = Field(..., description="Department name")
    parent_department_id: Optional[str] = Field(
        None,
        alias="parent_department_id",
        description="Parent department ID",
    )
    department_path: Optional[str] = Field(
        None,
        alias="department_path",
        description="Full department path",
    )
    order: int = Field(default=0, description="Sort order")
    member_count: Optional[int] = Field(
        None,
        alias="member_count",
        description="Number of members",
    )
    status: Optional[int] = Field(
        default=0,
        description="Department status (0=active, 1=deleted)",
    )

    @field_validator("status")
    @classmethod
    def is_active_from_status(cls, v: Optional[int]) -> bool:
        """Convert status to is_active boolean."""
        return v == 0 if v is not None else True


class FeishuUserRaw(BaseModel):
    """Raw user data from Feishu API.

    Schema for /contact/v3/users response.
    """

    model_config = ConfigDict(populate_by_name=True)

    user_id: str = Field(..., alias="user_id")
    union_id: Optional[str] = Field(None, alias="union_id")
    open_id: Optional[str] = Field(None, alias="open_id")
    name: str = Field(..., description="User name")
    en_name: Optional[str] = Field(None, alias="en_name")
    email: Optional[str] = Field(None, description="Email address")
    mobile: Optional[str] = Field(None, description="Mobile phone")
    job_title: Optional[str] = Field(
        None,
        alias="job_title",
        description="Job title",
    )
    employee_no: Optional[str] = Field(
        None,
        alias="employee_no",
        description="Employee number",
    )
    employee_type: Optional[int] = Field(
        None,
        alias="employee_type",
        description="Employee type (1=formal, 2=intern, etc.)",
    )
    avatar: Optional[FeishuAvatar] = Field(None)
    department_ids: List[str] = Field(
        default_factory=list,
        alias="department_ids",
        description="List of department IDs",
    )
    status: Optional[UserStatus] = Field(
        default=None,
        description="User status object",
    )
    is_tenant_manager: Optional[bool] = Field(
        None,
        alias="is_tenant_manager",
        description="Is tenant admin",
    )
    join_time: Optional[int] = Field(
        None,
        alias="join_time",
        description="Join timestamp in seconds",
    )

    @field_validator("department_ids", mode="before")
    @classmethod
    def ensure_list(cls, v: Any) -> List[str]:
        """Ensure department_ids is a list."""
        if v is None:
            return []
        if isinstance(v, list):
            return v
        return [v]

    @property
    def is_active(self) -> bool:
        """Check if user is active based on status."""
        if self.status is None:
            return True
        return self.status.is_active


class FeishuDepartmentListResponse(BaseModel):
    """Response schema for department list API."""

    has_more: bool = Field(default=False)
    items: List[FeishuDepartmentRaw] = Field(default_factory=list)
    page_token: Optional[str] = Field(None, alias="page_token")


class FeishuUserListResponse(BaseModel):
    """Response schema for user list API."""

    has_more: bool = Field(default=False)
    items: List[FeishuUserRaw] = Field(default_factory=list)
    page_token: Optional[str] = Field(None, alias="page_token")


class FeishuTokenResponse(BaseModel):
    """Response schema for access token API."""

    code: int = Field(..., description="Response code, 0 means success")
    msg: str = Field(..., description="Response message")
    tenant_access_token: Optional[str] = Field(
        None,
        alias="tenant_access_token",
        description="Tenant access token",
    )
    expire: Optional[int] = Field(
        None,
        description="Token expiration time in seconds",
    )

    @property
    def is_success(self) -> bool:
        """Check if the API call was successful."""
        return self.code == 0


class FeishuTokenData(BaseModel):
    """Structured token data for internal use."""

    token: str
    expires_at: datetime
    expires_in: int


class FeishuTaskRaw(BaseModel):
    """Raw task data from Feishu API.

    Schema for task-related endpoints.
    """

    model_config = ConfigDict(populate_by_name=True)

    task_id: str = Field(..., alias="task_id")
    summary: str = Field(..., description="Task summary/title")
    description: Optional[str] = Field(None, description="Task description")
    status: str = Field(..., description="Task status")
    due_time: Optional[int] = Field(
        None,
        alias="due_time",
        description="Due timestamp in milliseconds",
    )
    completed_time: Optional[int] = Field(
        None,
        alias="completed_time",
        description="Completion timestamp in milliseconds",
    )
    creator_id: Optional[str] = Field(
        None,
        alias="creator_id",
        description="Creator user ID",
    )
    assignee_ids: List[str] = Field(
        default_factory=list,
        alias="assignee_ids",
        description="Assignee user IDs",
    )
    follower_ids: List[str] = Field(
        default_factory=list,
        alias="follower_ids",
        description="Follower user IDs",
    )
    created_time: Optional[int] = Field(
        None,
        alias="created_time",
        description="Creation timestamp in milliseconds",
    )
    updated_time: Optional[int] = Field(
        None,
        alias="updated_time",
        description="Last update timestamp in milliseconds",
    )

    @field_validator("assignee_ids", "follower_ids", mode="before")
    @classmethod
    def ensure_list(cls, v: Any) -> List[str]:
        """Ensure fields are lists."""
        if v is None:
            return []
        if isinstance(v, list):
            return v
        return [v]


class FeishuTaskListResponse(BaseModel):
    """Response schema for task list API."""

    has_more: bool = Field(default=False)
    items: List[FeishuTaskRaw] = Field(default_factory=list)
    page_token: Optional[str] = Field(None, alias="page_token")


class FeishuProjectRaw(BaseModel):
    """Raw project data from Feishu Project API."""

    model_config = ConfigDict(populate_by_name=True)

    project_id: str = Field(..., alias="project_id")
    name: str = Field(..., description="Project name")
    description: Optional[str] = Field(None, description="Project description")
    status: str = Field(..., description="Project status")
    start_time: Optional[int] = Field(
        None,
        alias="start_time",
        description="Start timestamp in milliseconds",
    )
    end_time: Optional[int] = Field(
        None,
        alias="end_time",
        description="End timestamp in milliseconds",
    )
    owner_id: Optional[str] = Field(
        None,
        alias="owner_id",
        description="Project owner user ID",
    )
    member_ids: List[str] = Field(
        default_factory=list,
        alias="member_ids",
        description="Project member user IDs",
    )
    created_time: Optional[int] = Field(
        None,
        alias="created_time",
        description="Creation timestamp in milliseconds",
    )
    updated_time: Optional[int] = Field(
        None,
        alias="updated_time",
        description="Last update timestamp in milliseconds",
    )

    @field_validator("member_ids", mode="before")
    @classmethod
    def ensure_list(cls, v: Any) -> List[str]:
        """Ensure member_ids is a list."""
        if v is None:
            return []
        if isinstance(v, list):
            return v
        return [v]


class FeishuProjectListResponse(BaseModel):
    """Response schema for project list API."""

    has_more: bool = Field(default=False)
    items: List[FeishuProjectRaw] = Field(default_factory=list)
    page_token: Optional[str] = Field(None, alias="page_token")


class FeishuOKRRaw(BaseModel):
    """Raw OKR data from Feishu OKR API."""

    model_config = ConfigDict(populate_by_name=True)

    okr_id: str = Field(..., alias="okr_id")
    objective: str = Field(..., description="Objective description")
    key_results: List[Dict[str, Any]] = Field(
        default_factory=list,
        alias="key_results",
        description="Key results",
    )
    progress: int = Field(default=0, description="Progress percentage (0-100)")
    owner_id: Optional[str] = Field(
        None,
        alias="owner_id",
        description="OKR owner user ID",
    )
    cycle: str = Field(..., description="OKR cycle (e.g., 2026-Q1)")
    parent_okr_id: Optional[str] = Field(
        None,
        alias="parent_okr_id",
        description="Parent OKR ID for alignment",
    )
    created_time: Optional[int] = Field(
        None,
        alias="created_time",
        description="Creation timestamp in milliseconds",
    )
    updated_time: Optional[int] = Field(
        None,
        alias="updated_time",
        description="Last update timestamp in milliseconds",
    )
