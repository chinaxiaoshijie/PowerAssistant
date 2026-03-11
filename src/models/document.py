"""Database models for Feishu document synchronization.

This module defines SQLAlchemy models for storing Feishu document
metadata and content summaries.
"""

from datetime import datetime
from typing import List, Optional

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database import Base


class FeishuDocument(Base):
    """Model for storing Feishu document metadata.

    Attributes:
        id: Internal database ID
        document_id: Feishu document ID (unique identifier)
        title: Document title
        url: Document URL
        owner_id: Owner's Feishu user ID
        owner_name: Owner's display name
        create_time: Document creation time
        update_time: Document last update time
        last_sync_time: Last synchronization timestamp
        content_summary: Brief summary of document content
        headings: Document headings structure (JSON)
        word_count: Estimated word count
        is_deleted: Whether document is deleted in Feishu
        sync_status: Last sync status (success/failed/pending)
        sync_error: Error message if last sync failed
    """

    __tablename__ = "feishu_documents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    document_id: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        index=True,
        nullable=False,
        comment="Feishu document ID",
    )
    title: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
        comment="Document title",
    )
    url: Mapped[Optional[str]] = mapped_column(
        String(1000),
        nullable=True,
        comment="Document URL",
    )
    owner_id: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        index=True,
        comment="Owner's Feishu user ID",
    )
    owner_name: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        comment="Owner's display name",
    )

    # Timestamps
    create_time: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Document creation time in Feishu",
    )
    update_time: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Document last update time in Feishu",
    )
    last_sync_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        comment="Last synchronization timestamp",
    )

    # Content metadata
    content_summary: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Brief summary of document content",
    )
    headings: Mapped[List[dict]] = mapped_column(
        JSON,
        default=list,
        comment="Document headings structure",
    )
    word_count: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="Estimated word count",
    )

    # Status flags
    is_deleted: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        comment="Whether document is deleted in Feishu",
    )
    sync_status: Mapped[str] = mapped_column(
        String(50),
        default="pending",
        comment="Last sync status: success/failed/pending",
    )
    sync_error: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Error message if last sync failed",
    )

    # Relationships
    content_versions: Mapped[List["FeishuDocumentContent"]] = relationship(
        "FeishuDocumentContent",
        back_populates="document",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<FeishuDocument(id={self.id}, document_id={self.document_id}, title={self.title})>"


class FeishuDocumentContent(Base):
    """Model for storing Feishu document content versions.

    Stores historical versions of document content for tracking changes.

    Attributes:
        id: Internal database ID
        document_id: Reference to FeishuDocument.document_id
        revision: Document revision number
        content_text: Full text content
        content_blocks: Structured content blocks (JSON)
        captured_at: When this version was captured
    """

    __tablename__ = "feishu_document_contents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    document_id: Mapped[str] = mapped_column(
        String(255),
        ForeignKey("feishu_documents.document_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Reference to FeishuDocument",
    )
    revision: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="Document revision number",
    )
    content_text: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Full text content",
    )
    content_blocks: Mapped[List[dict]] = mapped_column(
        JSON,
        default=list,
        comment="Structured content blocks",
    )
    captured_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        comment="When this version was captured",
    )

    # Relationships
    document: Mapped["FeishuDocument"] = relationship(
        "FeishuDocument",
        back_populates="content_versions",
    )

    def __repr__(self) -> str:
        return f"<FeishuDocumentContent(id={self.id}, document_id={self.document_id}, revision={self.revision})>"


class DocumentSyncLog(Base):
    """Model for tracking document synchronization operations.

    Attributes:
        id: Internal database ID
        sync_type: Type of sync (full/incremental/single)
        started_at: When sync started
        completed_at: When sync completed
        status: Sync status (success/failed/running)
        documents_processed: Number of documents processed
        documents_created: Number of new documents created
        documents_updated: Number of documents updated
        documents_failed: Number of documents failed to sync
        error_message: Error details if sync failed
    """

    __tablename__ = "document_sync_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    sync_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="Type of sync: full/incremental/single",
    )
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        comment="When sync started",
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="When sync completed",
    )
    status: Mapped[str] = mapped_column(
        String(50),
        default="running",
        comment="Sync status: success/failed/running",
    )
    documents_processed: Mapped[int] = mapped_column(
        Integer,
        default=0,
        comment="Number of documents processed",
    )
    documents_created: Mapped[int] = mapped_column(
        Integer,
        default=0,
        comment="Number of new documents created",
    )
    documents_updated: Mapped[int] = mapped_column(
        Integer,
        default=0,
        comment="Number of documents updated",
    )
    documents_failed: Mapped[int] = mapped_column(
        Integer,
        default=0,
        comment="Number of documents failed to sync",
    )
    error_message: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Error details if sync failed",
    )

    def __repr__(self) -> str:
        return f"<DocumentSyncLog(id={self.id}, type={self.sync_type}, status={self.status})>"
