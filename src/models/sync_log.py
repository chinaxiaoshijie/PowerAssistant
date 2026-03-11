"""Sync log model for tracking synchronization operations.

This module provides audit logging for all data synchronization
operations from Feishu.
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from src.database import Base


class SyncLog(Base):
    """Audit log for synchronization operations.

    Tracks all sync operations including full and incremental syncs
    for both departments and employees.

    Attributes:
        id: Internal database primary key
        sync_type: Type of sync (full/incremental)
        entity_type: Type of entity synced (department/employee)
        records_fetched: Number of records fetched from Feishu
        records_created: Number of new records created
        records_updated: Number of existing records updated
        records_deactivated: Number of records marked inactive
        started_at: When sync operation started
        completed_at: When sync operation completed (null if in progress)
        status: Sync status (success/failed/partial/in_progress)
        error_message: Error details if sync failed
        duration_seconds: Sync duration in seconds
    """

    __tablename__ = "sync_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    sync_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        comment="Sync type: full/incremental",
    )
    entity_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        comment="Entity type: department/employee",
    )
    records_fetched: Mapped[int] = mapped_column(
        default=0,
        nullable=False,
        comment="Records fetched from Feishu",
    )
    records_created: Mapped[int] = mapped_column(
        default=0,
        nullable=False,
        comment="New records created",
    )
    records_updated: Mapped[int] = mapped_column(
        default=0,
        nullable=False,
        comment="Existing records updated",
    )
    records_deactivated: Mapped[int] = mapped_column(
        default=0,
        nullable=False,
        comment="Records marked inactive",
    )
    started_at: Mapped[datetime] = mapped_column(
        default=datetime.utcnow,
        nullable=False,
        comment="Sync start time",
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        nullable=True,
        comment="Sync completion time",
    )
    status: Mapped[str] = mapped_column(
        String(20),
        default="in_progress",
        nullable=False,
        comment="Sync status: success/failed/partial/in_progress",
    )
    error_message: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Error details if failed",
    )
    duration_seconds: Mapped[Optional[int]] = mapped_column(
        nullable=True,
        comment="Sync duration in seconds",
    )

    __table_args__ = (
        Index(
            "ix_sync_logs_entity_status",
            "entity_type",
            "status",
        ),
        Index(
            "ix_sync_logs_started_at",
            "started_at",
        ),
    )

    def __repr__(self) -> str:
        """Return string representation of sync log."""
        return (
            f"<SyncLog(id={self.id}, type='{self.sync_type}', "
            f"entity='{self.entity_type}', status='{self.status}')>"
        )

    def complete(
        self,
        status: str,
        error_message: Optional[str] = None,
    ) -> None:
        """Mark sync as completed.

        Args:
            status: Final status (success/failed/partial)
            error_message: Optional error message if failed
        """
        self.completed_at = datetime.utcnow()
        self.status = status
        self.error_message = error_message
        if self.started_at:
            delta = self.completed_at - self.started_at
            self.duration_seconds = int(delta.total_seconds())

    @property
    def is_success(self) -> bool:
        """Check if sync completed successfully."""
        return self.status == "success"

    @property
    def is_failed(self) -> bool:
        """Check if sync failed."""
        return self.status == "failed"
