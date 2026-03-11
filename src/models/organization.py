"""Organization structure models for Feishu sync.

This module defines SQLAlchemy models for departments and employees
synchronized from Feishu organization structure.
"""

from datetime import date, datetime
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import JSON, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database import Base

if TYPE_CHECKING:
    from src.models.sync_log import SyncLog


class Department(Base):
    """Department model synchronized from Feishu.

    Represents an organizational unit with hierarchical structure support.

    Attributes:
        id: Internal database primary key
        feishu_dept_id: Unique Feishu department ID (external reference)
        name: Department name
        parent_id: Reference to parent department's feishu_dept_id
        order: Sort order within parent department
        is_active: Whether department is currently active
        created_at: Record creation timestamp
        updated_at: Last update timestamp
        sync_updated_at: Last sync from Feishu timestamp
    """

    __tablename__ = "departments"

    id: Mapped[int] = mapped_column(primary_key=True)
    feishu_dept_id: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        index=True,
        nullable=False,
        comment="Feishu department ID",
    )
    name: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
        comment="Department name",
    )
    parent_id: Mapped[Optional[str]] = mapped_column(
        ForeignKey("departments.feishu_dept_id"),
        nullable=True,
        comment="Parent department Feishu ID",
    )
    order: Mapped[int] = mapped_column(
        default=0,
        comment="Sort order within parent",
    )
    is_active: Mapped[bool] = mapped_column(
        default=True,
        comment="Whether department is active",
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

    # Relationships
    parent: Mapped[Optional["Department"]] = relationship(
        "Department",
        back_populates="children",
        remote_side="Department.feishu_dept_id",
    )
    children: Mapped[List["Department"]] = relationship(
        "Department",
        back_populates="parent",
        lazy="selectin",
    )
    # Note: employees relationship removed - use property method instead
    # since Employee uses JSON field for department_ids (many-to-many)

    __table_args__ = (
        Index(
            "ix_departments_parent_active",
            "parent_id",
            "is_active",
        ),
    )

    def __repr__(self) -> str:
        """Return string representation of department."""
        return f"<Department(id={self.id}, name='{self.name}', feishu_id='{self.feishu_dept_id}')>"

    def get_employees(self, session) -> List["Employee"]:
        """Get employees belonging to this department.

        Args:
            session: SQLAlchemy session for querying

        Returns:
            List of Employee objects in this department
        """
        from sqlalchemy import select, func

        # Query employees where this department ID is in their department_ids JSON array
        stmt = select(Employee).where(
            Employee.department_ids.contains([self.feishu_dept_id])
        )
        return session.execute(stmt).scalars().all()

    @property
    def full_path(self) -> str:
        """Get full department path (e.g., 'Company/Dept/SubDept')."""
        if self.parent is None:
            return self.name
        return f"{self.parent.full_path}/{self.name}"

    @property
    def level(self) -> int:
        """Get department level in hierarchy (0 = root)."""
        if self.parent is None:
            return 0
        return self.parent.level + 1


class Employee(Base):
    """Employee model synchronized from Feishu.

    Represents an employee with their organizational associations.

    Attributes:
        id: Internal database primary key
        feishu_user_id: Unique Feishu user ID (external reference)
        name: Employee name
        email: Work email address
        mobile: Mobile phone number
        job_title: Job title/position
        employee_no: Employee number/staff ID
        avatar_url: Profile avatar URL
        department_ids: List of department Feishu IDs (JSON)
        role_type: Role classification (研发/交付/产品/管理)
        join_date: Date when employee joined
        is_active: Whether employee is currently active
        is_admin: Whether employee has admin privileges
        created_at: Record creation timestamp
        updated_at: Last update timestamp
        sync_updated_at: Last sync from Feishu timestamp
    """

    __tablename__ = "employees"

    id: Mapped[int] = mapped_column(primary_key=True)
    feishu_user_id: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        index=True,
        nullable=False,
        comment="Feishu user ID",
    )
    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="Employee name",
    )
    email: Mapped[Optional[str]] = mapped_column(
        String(200),
        nullable=True,
        comment="Work email",
    )
    mobile: Mapped[Optional[str]] = mapped_column(
        String(20),
        nullable=True,
        comment="Mobile phone",
    )
    job_title: Mapped[Optional[str]] = mapped_column(
        String(200),
        nullable=True,
        comment="Job title",
    )
    employee_no: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        index=True,
        comment="Employee number",
    )
    avatar_url: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Avatar URL",
    )
    department_ids: Mapped[list] = mapped_column(
        JSON,
        default=list,
        nullable=False,
        comment="List of department Feishu IDs",
    )
    role_type: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        comment="Role type (研发/交付/产品/管理)",
    )
    join_date: Mapped[Optional[date]] = mapped_column(
        nullable=True,
        comment="Join date",
    )
    is_active: Mapped[bool] = mapped_column(
        default=True,
        nullable=False,
        comment="Whether employee is active",
    )
    is_admin: Mapped[bool] = mapped_column(
        default=False,
        nullable=False,
        comment="Whether employee is admin",
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

    # Note: departments relationship uses JSON field for many-to-many
    # To get actual department objects, use get_departments() method with session

    __table_args__ = (
        Index(
            "ix_employees_active_role",
            "is_active",
            "role_type",
        ),
        Index(
            "ix_employees_name",
            "name",
        ),
    )

    def get_departments(self, session) -> List["Department"]:
        """Get department objects for this employee.

        Args:
            session: SQLAlchemy session for querying

        Returns:
            List of Department objects this employee belongs to
        """
        from sqlalchemy import select

        if not self.department_ids:
            return []

        stmt = select(Department).where(
            Department.feishu_dept_id.in_(self.department_ids)
        )
        return session.execute(stmt).scalars().all()

    def __repr__(self) -> str:
        """Return string representation of employee."""
        return f"<Employee(id={self.id}, name='{self.name}', feishu_id='{self.feishu_user_id}')>"

    def belongs_to_department(self, dept_id: str) -> bool:
        """Check if employee belongs to a specific department.

        Args:
            dept_id: Feishu department ID to check

        Returns:
            True if employee is in the department
        """
        return dept_id in (self.department_ids or [])
