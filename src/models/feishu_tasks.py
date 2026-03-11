"""Feishu task and project models for R&D health metrics."""

from datetime import date, datetime
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import JSON, ForeignKey, Index, String, Text, Float, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database import Base

if TYPE_CHECKING:
    from src.models.organization import Employee


class FeishuTask(Base):
    """Feishu task model for R&D health tracking.

    Attributes:
        id: Internal database primary key
        feishu_task_id: Unique Feishu task ID (external reference)
        title: Task title
        description: Task description
        status: Task status (pending/in_progress/done/cancelled)
        priority: Priority level (p0/p1/p2/p3)
        due_date: Task due date
        completed_at: Task completion timestamp
        assignee_ids: List of assigned employee Feishu IDs
        reporter_id: Task reporter Feishu ID
        project_id: Associated project ID
        parent_task_id: Parent task ID for subtasks
        labels: Task labels/tags (JSON)
        is_tech_debt: Whether this task is technical debt
        story_points: Story points for effort estimation
        actual_hours: Actual hours spent
        estimated_hours: Estimated hours
        created_at: Record creation timestamp
        updated_at: Last update timestamp
        sync_updated_at: Last sync from Feishu timestamp
    """

    __tablename__ = "feishu_tasks"

    id: Mapped[int] = mapped_column(primary_key=True)
    feishu_task_id: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        index=True,
        nullable=False,
        comment="Feishu task ID",
    )
    title: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
        comment="Task title",
    )
    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Task description",
    )
    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="pending",
        comment="Task status",
    )
    priority: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="p2",
        comment="Priority level (p0/p1/p2/p3)",
    )
    due_date: Mapped[Optional[date]] = mapped_column(
        nullable=True,
        comment="Task due date",
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        nullable=True,
        comment="Task completion timestamp",
    )
    assignee_ids: Mapped[list] = mapped_column(
        JSON,
        default=list,
        nullable=False,
        comment="List of assigned employee Feishu IDs",
    )
    reporter_id: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        comment="Task reporter Feishu ID",
    )
    project_id: Mapped[Optional[str]] = mapped_column(
        String(100),
        index=True,
        nullable=True,
        comment="Associated project Feishu ID",
    )
    parent_task_id: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        comment="Parent task Feishu ID",
    )
    labels: Mapped[list] = mapped_column(
        JSON,
        default=list,
        nullable=False,
        comment="Task labels/tags",
    )
    is_tech_debt: Mapped[bool] = mapped_column(
        default=False,
        nullable=False,
        comment="Whether this task is technical debt",
    )
    story_points: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
        comment="Story points for effort estimation",
    )
    actual_hours: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
        comment="Actual hours spent",
    )
    estimated_hours: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
        comment="Estimated hours",
    )
    created_at: Mapped[datetime] = mapped_column(
        default=datetime.utcnow,
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )
    sync_updated_at: Mapped[datetime] = mapped_column(
        default=datetime.utcnow,
        nullable=False,
        comment="Last sync timestamp from Feishu",
    )

    __table_args__ = (
        Index("ix_feishu_tasks_status", "status"),
        Index("ix_feishu_tasks_priority", "priority"),
        Index("ix_feishu_tasks_due_date", "due_date"),
        Index("ix_feishu_tasks_assignee", "assignee_ids", postgresql_using="gin"),
    )

    def __repr__(self) -> str:
        return f"<FeishuTask(id={self.id}, title='{self.title[:50]}', status='{self.status}')>"

    @property
    def is_overdue(self) -> bool:
        """Check if task is overdue."""
        if self.due_date is None or self.status == "done":
            return False
        return datetime.utcnow().date() > self.due_date

    @property
    def is_done(self) -> bool:
        """Check if task is completed."""
        return self.status == "done"


class FeishuProject(Base):
    """Feishu project model for delivery health tracking.

    Attributes:
        id: Internal database primary key
        feishu_project_id: Unique Feishu project ID
        name: Project name
        description: Project description
        status: Project status (planning/in_progress/done/cancelled)
        start_date: Project start date
        end_date: Project planned end date
        actual_end_date: Project actual end date
        owner_id: Project owner Feishu ID
        member_ids: List of member Feishu IDs
        milestones: Project milestones (JSON)
        risk_level: Risk level (low/medium/high/critical)
        progress: Progress percentage (0-100)
        created_at: Record creation timestamp
        updated_at: Last update timestamp
        sync_updated_at: Last sync from Feishu timestamp
    """

    __tablename__ = "feishu_projects"

    id: Mapped[int] = mapped_column(primary_key=True)
    feishu_project_id: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        index=True,
        nullable=False,
        comment="Feishu project ID",
    )
    name: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
        comment="Project name",
    )
    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Project description",
    )
    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="planning",
        comment="Project status",
    )
    start_date: Mapped[Optional[date]] = mapped_column(
        nullable=True,
        comment="Project start date",
    )
    end_date: Mapped[Optional[date]] = mapped_column(
        nullable=True,
        comment="Project planned end date",
    )
    actual_end_date: Mapped[Optional[date]] = mapped_column(
        nullable=True,
        comment="Project actual end date",
    )
    owner_id: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        comment="Project owner Feishu ID",
    )
    member_ids: Mapped[list] = mapped_column(
        JSON,
        default=list,
        nullable=False,
        comment="List of member Feishu IDs",
    )
    milestones: Mapped[list] = mapped_column(
        JSON,
        default=list,
        nullable=False,
        comment="Project milestones",
    )
    risk_level: Mapped[str] = mapped_column(
        String(20),
        default="low",
        comment="Risk level (low/medium/high/critical)",
    )
    progress: Mapped[int] = mapped_column(
        Integer,
        default=0,
        comment="Progress percentage (0-100)",
    )
    created_at: Mapped[datetime] = mapped_column(
        default=datetime.utcnow,
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )
    sync_updated_at: Mapped[datetime] = mapped_column(
        default=datetime.utcnow,
        nullable=False,
        comment="Last sync timestamp from Feishu",
    )

    __table_args__ = (
        Index("ix_feishu_projects_status", "status"),
        Index("ix_feishu_projects_risk", "risk_level"),
    )

    def __repr__(self) -> str:
        return f"<FeishuProject(id={self.id}, name='{self.name}', status='{self.status}')>"

    @property
    def is_delayed(self) -> bool:
        """Check if project is delayed."""
        if self.end_date is None or self.status == "done":
            return False
        return datetime.utcnow().date() > self.end_date


class FeishuOKR(Base):
    """Feishu OKR model for goal tracking.

    Attributes:
        id: Internal database primary key
        feishu_okr_id: Unique Feishu OKR ID
        objective: Objective description
        key_results: Key results (JSON)
        progress: Progress percentage (0-100)
        owner_id: OKR owner Feishu ID
        cycle: OKR cycle (e.g., "2026-Q1")
        parent_okr_id: Parent OKR ID for alignment
        created_at: Record creation timestamp
        updated_at: Last update timestamp
        sync_updated_at: Last sync from Feishu timestamp
    """

    __tablename__ = "feishu_okrs"

    id: Mapped[int] = mapped_column(primary_key=True)
    feishu_okr_id: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        index=True,
        nullable=False,
        comment="Feishu OKR ID",
    )
    objective: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
        comment="Objective description",
    )
    key_results: Mapped[list] = mapped_column(
        JSON,
        default=list,
        nullable=False,
        comment="Key results",
    )
    progress: Mapped[int] = mapped_column(
        Integer,
        default=0,
        comment="Progress percentage (0-100)",
    )
    owner_id: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        comment="OKR owner Feishu ID",
    )
    cycle: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="OKR cycle (e.g., 2026-Q1)",
    )
    parent_okr_id: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        comment="Parent OKR ID for alignment",
    )
    created_at: Mapped[datetime] = mapped_column(
        default=datetime.utcnow,
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )
    sync_updated_at: Mapped[datetime] = mapped_column(
        default=datetime.utcnow,
        nullable=False,
        comment="Last sync timestamp from Feishu",
    )

    __table_args__ = (
        Index("ix_feishu_okrs_cycle", "cycle"),
        Index("ix_feishu_okrs_owner", "owner_id"),
    )

    def __repr__(self) -> str:
        return f"<FeishuOKR(id={self.id}, objective='{self.objective[:50]}', cycle='{self.cycle}')>"
