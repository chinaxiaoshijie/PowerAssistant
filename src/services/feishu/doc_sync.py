"""Document synchronization service for Feishu documents.

This module provides services for synchronizing Feishu documents
to the local database, including metadata and content extraction.
"""

from datetime import datetime
from typing import List, Optional

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.document import (
    DocumentSyncLog,
    FeishuDocument,
    FeishuDocumentContent,
)
from src.schemas.feishu_docs import FeishuDocRaw
from src.services.feishu.client import FeishuClient


logger = structlog.get_logger()


class DocumentSyncService:
    """Service for synchronizing Feishu documents.

    This service handles:
    - Document metadata synchronization
    - Document content extraction and storage
    - Change tracking and versioning
    - Sync status management
    """

    def __init__(
        self,
        db_session: AsyncSession,
        feishu_client: Optional[FeishuClient] = None,
    ):
        """Initialize the document sync service.

        Args:
            db_session: Database session for persistence
            feishu_client: Feishu API client (optional, will create if not provided)
        """
        self._db = db_session
        self._client = feishu_client
        self._logger = logger.bind(component="DocumentSyncService")

    async def _get_client(self) -> FeishuClient:
        """Get or create Feishu client."""
        if self._client is None:
            self._client = FeishuClient()
            await self._client.__aenter__()
        return self._client

    async def sync_document(
        self,
        document_id: str,
        sync_content: bool = True,
    ) -> FeishuDocument:
        """Synchronize a single document from Feishu.

        Args:
            document_id: Feishu document ID
            sync_content: Whether to sync document content

        Returns:
            Synchronized document record
        """
        self._logger.info("syncing_document", document_id=document_id)

        client = await self._get_client()

        try:
            # Fetch document metadata from Feishu
            doc_raw = await client.get_document(document_id)

            # Check if document exists in database
            result = await self._db.execute(
                select(FeishuDocument).where(
                    FeishuDocument.document_id == document_id
                )
            )
            doc_record = result.scalar_one_or_none()

            # Create or update document record
            if doc_record is None:
                doc_record = FeishuDocument(document_id=document_id)
                self._db.add(doc_record)
                self._logger.info("creating_new_document_record", document_id=document_id)
            else:
                self._logger.info("updating_existing_document_record", document_id=document_id)

            # Update metadata
            doc_record.title = doc_raw.title
            doc_record.url = doc_raw.url
            doc_record.owner_id = doc_raw.owner_id
            if doc_raw.owner:
                # Try to get owner name from owner info
                doc_record.owner_name = doc_raw.owner.user_id
            doc_record.create_time = doc_raw.create_datetime
            doc_record.update_time = doc_raw.update_datetime
            doc_record.is_deleted = doc_raw.is_deleted
            doc_record.sync_status = "success"
            doc_record.sync_error = None

            # Sync content if requested
            if sync_content and not doc_raw.is_deleted:
                await self._sync_document_content(doc_record)

            await self._db.commit()
            await self._db.refresh(doc_record)

            self._logger.info(
                "document_sync_completed",
                document_id=document_id,
                title=doc_record.title,
            )

            return doc_record

        except Exception as e:
            self._logger.error(
                "document_sync_failed",
                document_id=document_id,
                error=str(e),
            )

            # Update or create record with error status
            result = await self._db.execute(
                select(FeishuDocument).where(
                    FeishuDocument.document_id == document_id
                )
            )
            doc_record = result.scalar_one_or_none()

            if doc_record:
                doc_record.sync_status = "failed"
                doc_record.sync_error = str(e)
            else:
                doc_record = FeishuDocument(
                    document_id=document_id,
                    sync_status="failed",
                    sync_error=str(e),
                )
                self._db.add(doc_record)

            await self._db.commit()
            raise

    async def _sync_document_content(self, doc_record: FeishuDocument) -> None:
        """Sync document content and extract metadata.

        Args:
            doc_record: Document record to sync content for
        """
        self._logger.info(
            "syncing_document_content",
            document_id=doc_record.document_id,
        )

        client = await self._get_client()

        # Fetch document content
        content = await client.get_document_content(doc_record.document_id)

        # Extract text content
        full_text = content.get_all_text()
        headings = content.get_headings()

        # Update document record with extracted metadata
        doc_record.headings = headings
        doc_record.word_count = len(full_text) if full_text else 0

        # Create content summary (first 2000 characters)
        if full_text:
            doc_record.content_summary = full_text[:2000]

        # Create content version record
        content_version = FeishuDocumentContent(
            document_id=doc_record.document_id,
            revision=content.revision,
            content_text=full_text,
            content_blocks=[
                {"block_id": b.block_id, "type": b.block_type, "text": b.content_text}
                for b in content.blocks
            ],
        )
        self._db.add(content_version)

        self._logger.info(
            "document_content_synced",
            document_id=doc_record.document_id,
            word_count=doc_record.word_count,
            headings_count=len(headings),
        )

    async def sync_documents_by_ids(
        self,
        document_ids: List[str],
        sync_content: bool = True,
    ) -> DocumentSyncLog:
        """Sync multiple documents by their IDs.

        Args:
            document_ids: List of Feishu document IDs
            sync_content: Whether to sync document content

        Returns:
            Sync log record
        """
        self._logger.info(
            "starting_batch_document_sync",
            document_count=len(document_ids),
        )

        # Create sync log
        sync_log = DocumentSyncLog(
            sync_type="batch",
            status="running",
            documents_processed=len(document_ids),
        )
        self._db.add(sync_log)
        await self._db.commit()
        await self._db.refresh(sync_log)

        created_count = 0
        updated_count = 0
        failed_count = 0

        client = await self._get_client()

        try:
            for doc_id in document_ids:
                try:
                    # Check if document exists
                    result = await self._db.execute(
                        select(FeishuDocument).where(
                            FeishuDocument.document_id == doc_id
                        )
                    )
                    existing = result.scalar_one_or_none()

                    # Sync document
                    await self.sync_document(doc_id, sync_content=sync_content)

                    if existing:
                        updated_count += 1
                    else:
                        created_count += 1

                except Exception as e:
                    self._logger.error(
                        "batch_sync_document_failed",
                        document_id=doc_id,
                        error=str(e),
                    )
                    failed_count += 1

            # Update sync log
            sync_log.status = "success" if failed_count == 0 else "partial"
            sync_log.documents_created = created_count
            sync_log.documents_updated = updated_count
            sync_log.documents_failed = failed_count
            sync_log.completed_at = datetime.utcnow()

            await self._db.commit()

            self._logger.info(
                "batch_document_sync_completed",
                created=created_count,
                updated=updated_count,
                failed=failed_count,
            )

            return sync_log

        except Exception as e:
            sync_log.status = "failed"
            sync_log.error_message = str(e)
            sync_log.completed_at = datetime.utcnow()
            await self._db.commit()
            raise

    async def get_document_by_id(
        self,
        document_id: str,
    ) -> Optional[FeishuDocument]:
        """Get document from database by ID.

        Args:
            document_id: Feishu document ID

        Returns:
            Document record or None
        """
        result = await self._db.execute(
            select(FeishuDocument).where(
                FeishuDocument.document_id == document_id
            )
        )
        return result.scalar_one_or_none()

    async def list_documents(
        self,
        owner_id: Optional[str] = None,
        sync_status: Optional[str] = None,
        is_deleted: Optional[bool] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[FeishuDocument]:
        """List documents from database with filters.

        Args:
            owner_id: Filter by owner
            sync_status: Filter by sync status
            is_deleted: Filter by deletion status
            limit: Maximum results
            offset: Skip offset

        Returns:
            List of document records
        """
        query = select(FeishuDocument)

        if owner_id:
            query = query.where(FeishuDocument.owner_id == owner_id)
        if sync_status:
            query = query.where(FeishuDocument.sync_status == sync_status)
        if is_deleted is not None:
            query = query.where(FeishuDocument.is_deleted == is_deleted)

        query = query.order_by(FeishuDocument.update_time.desc())
        query = query.limit(limit).offset(offset)

        result = await self._db.execute(query)
        return list(result.scalars().all())

    async def close(self) -> None:
        """Close resources."""
        if self._client:
            await self._client.close()
            self._client = None
