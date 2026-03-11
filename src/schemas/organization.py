"""Pydantic schemas for organization API responses.

These schemas define the structure of API responses for department
and employee queries.
"""

from datetime import date, datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class DepartmentBase(BaseModel):
    """Base department schema with common fields."""

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(..., description="Internal department ID")
    feishu_dept_id: str = Field(..., description="Feishu department ID")
    name: str = Field(..., description="Department name")
    order: int = Field(default=0, description="Sort order")
    is_active: bool = Field(default=True, description="Is department active")


class DepartmentResponse(DepartmentBase):
    """Department response schema with hierarchy."""

    parent_id: Optional[str] = Field(
        None,
        description="Parent department Feishu ID",
    )
    children: List["DepartmentResponse"] = Field(
        default_factory=list,
        description="Child departments",
    )
    employee_count: int = Field(
        default=0,
        description="Number of employees in department",
    )
    created_at: datetime = Field(..., description="Record creation time")
    updated_at: datetime = Field(..., description="Last update time")


class DepartmentTreeResponse(BaseModel):
    """Department tree structure response."""

    model_config = ConfigDict(from_attributes=True)

    departments: List[DepartmentResponse] = Field(
        default_factory=list,
        description="Root-level departments with nested children",
    )
    total_count: int = Field(..., description="Total department count")


class EmployeeBase(BaseModel):
    """Base employee schema with common fields."""

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(..., description="Internal employee ID")
    feishu_user_id: str = Field(..., description="Feishu user ID")
    name: str = Field(..., description="Employee name")
    job_title: Optional[str] = Field(None, description="Job title")
    is_active: bool = Field(default=True, description="Is employee active")


class EmployeeResponse(EmployeeBase):
    """Employee response schema with departments."""

    email: Optional[str] = Field(None, description="Work email")
    mobile: Optional[str] = Field(None, description="Mobile phone")
    employee_no: Optional[str] = Field(None, description="Employee number")
    avatar_url: Optional[str] = Field(None, description="Avatar URL")
    department_names: List[str] = Field(
        default_factory=list,
        description="Names of departments employee belongs to",
    )
    role_type: Optional[str] = Field(None, description="Role classification")
    join_date: Optional[date] = Field(None, description="Join date")
    is_admin: bool = Field(default=False, description="Is admin user")
    created_at: datetime = Field(..., description="Record creation time")
    updated_at: datetime = Field(..., description="Last update time")


class EmployeeDetailResponse(EmployeeResponse):
    """Detailed employee response with full information."""

    department_ids: List[str] = Field(
        default_factory=list,
        description="Feishu department IDs",
    )


class PaginatedResponse(BaseModel):
    """Generic paginated response wrapper."""

    items: List[Any] = Field(default_factory=list, description="Response items")
    total: int = Field(..., description="Total number of items")
    page: int = Field(default=1, description="Current page number")
    page_size: int = Field(default=50, description="Items per page")
    total_pages: int = Field(default=1, description="Total number of pages")

    @classmethod
    def create(
        cls,
        items: List[Any],
        total: int,
        page: int,
        page_size: int,
    ) -> "PaginatedResponse":
        """Create paginated response.

        Args:
            items: List of items for current page
            total: Total number of items
            page: Current page number
            page_size: Items per page

        Returns:
            PaginatedResponse instance
        """
        total_pages = (total + page_size - 1) // page_size if page_size > 0 else 1
        return cls(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )


class EmployeeListResponse(PaginatedResponse):
    """Paginated employee list response."""

    items: List[EmployeeResponse] = Field(
        default_factory=list,
        description="List of employees",
    )


class SyncStats(BaseModel):
    """Statistics for a sync operation."""

    records_fetched: int = Field(default=0, description="Records fetched")
    records_created: int = Field(default=0, description="Records created")
    records_updated: int = Field(default=0, description="Records updated")
    records_deactivated: int = Field(default=0, description="Records deactivated")
    errors: List[str] = Field(default_factory=list, description="Error messages")

    @property
    def total_processed(self) -> int:
        """Get total number of records processed."""
        return self.records_created + self.records_updated + self.records_deactivated


class SyncResultResponse(BaseModel):
    """Response schema for sync operation result."""

    sync_id: int = Field(..., description="Sync log ID")
    sync_type: str = Field(..., description="Type of sync (full/incremental)")
    entity_type: str = Field(..., description="Entity type (department/employee)")
    stats: SyncStats = Field(..., description="Sync statistics")
    status: str = Field(..., description="Sync status")
    started_at: datetime = Field(..., description="Sync start time")
    completed_at: Optional[datetime] = Field(None, description="Sync completion time")
    duration_seconds: Optional[int] = Field(None, description="Duration in seconds")


class SyncLogResponse(BaseModel):
    """Response schema for sync log entry."""

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(..., description="Sync log ID")
    sync_type: str = Field(..., description="Sync type")
    entity_type: str = Field(..., description="Entity type")
    records_fetched: int = Field(..., description="Records fetched")
    records_created: int = Field(..., description="Records created")
    records_updated: int = Field(..., description="Records updated")
    records_deactivated: int = Field(..., description="Records deactivated")
    started_at: datetime = Field(..., description="Start time")
    completed_at: Optional[datetime] = Field(None, description="Completion time")
    status: str = Field(..., description="Status")
    error_message: Optional[str] = Field(None, description="Error message")
    duration_seconds: Optional[int] = Field(None, description="Duration")


class SyncStatusResponse(BaseModel):
    """Response schema for current sync status."""

    last_sync_time: Optional[datetime] = Field(
        None,
        description="Last successful sync time",
    )
    next_scheduled_sync: Optional[datetime] = Field(
        None,
        description="Next scheduled sync time",
    )
    is_syncing: bool = Field(
        default=False,
        description="Whether sync is currently in progress",
    )
    recent_syncs: List[SyncLogResponse] = Field(
        default_factory=list,
        description="Recent sync log entries",
    )
    health: str = Field(
        default="unknown",
        description="Overall sync health (healthy/degraded/failed/unknown)",
    )


# Resolve forward references
DepartmentResponse.model_rebuild()
