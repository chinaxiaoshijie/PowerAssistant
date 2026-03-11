"""API endpoints for Feishu document synchronization and management."""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import get_db_session
from src.models.document import DocumentSyncLog, FeishuDocument
from src.schemas.feishu_docs import FeishuDocMeta
from src.services.feishu.doc_sync import DocumentSyncService

router = APIRouter(prefix="/documents", tags=["documents"])


@router.post("/sync/{document_id}", response_model=dict)
async def sync_document(
    document_id: str,
    sync_content: bool = True,
    db: AsyncSession = Depends(get_db_session),
) -> dict:
    """Sync a single document from Feishu.

    Args:
        document_id: Feishu document ID (e.g., doc_xxx or doxcnxxx)
        sync_content: Whether to sync document content

    Returns:
        Sync result with document metadata
    """
    service = DocumentSyncService(db)

    try:
        doc = await service.sync_document(document_id, sync_content=sync_content)

        return {
            "success": True,
            "document": {
                "id": doc.id,
                "document_id": doc.document_id,
                "title": doc.title,
                "url": doc.url,
                "owner_id": doc.owner_id,
                "owner_name": doc.owner_name,
                "sync_status": doc.sync_status,
                "last_sync_time": doc.last_sync_time.isoformat() if doc.last_sync_time else None,
                "word_count": doc.word_count,
            },
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to sync document: {str(e)}",
        )

    finally:
        await service.close()


@router.post("/sync-batch", response_model=dict)
async def sync_documents_batch(
    document_ids: List[str],
    sync_content: bool = True,
    db: AsyncSession = Depends(get_db_session),
) -> dict:
    """Sync multiple documents from Feishu.

    Args:
        document_ids: List of Feishu document IDs
        sync_content: Whether to sync document content

    Returns:
        Batch sync result with counts
    """
    service = DocumentSyncService(db)

    try:
        sync_log = await service.sync_documents_by_ids(
            document_ids,
            sync_content=sync_content,
        )

        return {
            "success": sync_log.status in ("success", "partial"),
            "sync_log": {
                "id": sync_log.id,
                "status": sync_log.status,
                "documents_processed": sync_log.documents_processed,
                "documents_created": sync_log.documents_created,
                "documents_updated": sync_log.documents_updated,
                "documents_failed": sync_log.documents_failed,
                "started_at": sync_log.started_at.isoformat() if sync_log.started_at else None,
                "completed_at": sync_log.completed_at.isoformat() if sync_log.completed_at else None,
            },
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to sync documents: {str(e)}",
        )

    finally:
        await service.close()


@router.get("/list", response_model=dict)
async def list_documents(
    owner_id: Optional[str] = None,
    sync_status: Optional[str] = None,
    is_deleted: Optional[bool] = False,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db_session),
) -> dict:
    """List synchronized documents.

    Args:
        owner_id: Filter by owner
        sync_status: Filter by sync status (success/failed/pending)
        is_deleted: Filter by deletion status
        limit: Maximum results
        offset: Skip offset

    Returns:
        List of documents with pagination info
    """
    service = DocumentSyncService(db)

    try:
        documents = await service.list_documents(
            owner_id=owner_id,
            sync_status=sync_status,
            is_deleted=is_deleted,
            limit=limit,
            offset=offset,
        )

        return {
            "documents": [
                {
                    "id": doc.id,
                    "document_id": doc.document_id,
                    "title": doc.title,
                    "url": doc.url,
                    "owner_id": doc.owner_id,
                    "owner_name": doc.owner_name,
                    "create_time": doc.create_time.isoformat() if doc.create_time else None,
                    "update_time": doc.update_time.isoformat() if doc.update_time else None,
                    "last_sync_time": doc.last_sync_time.isoformat() if doc.last_sync_time else None,
                    "sync_status": doc.sync_status,
                    "word_count": doc.word_count,
                    "headings_count": len(doc.headings) if doc.headings else 0,
                }
                for doc in documents
            ],
            "pagination": {
                "limit": limit,
                "offset": offset,
                "count": len(documents),
            },
        }

    finally:
        await service.close()


@router.get("/{document_id}", response_model=dict)
async def get_document(
    document_id: str,
    db: AsyncSession = Depends(get_db_session),
) -> dict:
    """Get document details.

    Args:
        document_id: Feishu document ID

    Returns:
        Document details with content metadata
    """
    service = DocumentSyncService(db)

    try:
        doc = await service.get_document_by_id(document_id)

        if not doc:
            raise HTTPException(
                status_code=404,
                detail=f"Document {document_id} not found",
            )

        return {
            "id": doc.id,
            "document_id": doc.document_id,
            "title": doc.title,
            "url": doc.url,
            "owner_id": doc.owner_id,
            "owner_name": doc.owner_name,
            "create_time": doc.create_time.isoformat() if doc.create_time else None,
            "update_time": doc.update_time.isoformat() if doc.update_time else None,
            "last_sync_time": doc.last_sync_time.isoformat() if doc.last_sync_time else None,
            "sync_status": doc.sync_status,
            "sync_error": doc.sync_error,
            "word_count": doc.word_count,
            "headings": doc.headings,
            "content_summary": doc.content_summary,
            "is_deleted": doc.is_deleted,
        }

    finally:
        await service.close()


@router.get("/{document_id}/content", response_model=dict)
async def get_document_content(
    document_id: str,
    db: AsyncSession = Depends(get_db_session),
) -> dict:
    """Get document content versions.

    Args:
        document_id: Feishu document ID

    Returns:
        Document with content versions
    """
    from sqlalchemy import select

    result = await db.execute(
        select(FeishuDocument).where(FeishuDocument.document_id == document_id)
    )
    doc = result.scalar_one_or_none()

    if not doc:
        raise HTTPException(
            status_code=404,
            detail=f"Document {document_id} not found",
        )

    # Load content versions
    content_versions = []
    for content in doc.content_versions:
        content_versions.append({
            "id": content.id,
            "revision": content.revision,
            "captured_at": content.captured_at.isoformat() if content.captured_at else None,
            "content_preview": content.content_text[:500] if content.content_text else None,
        })

    return {
        "document_id": doc.document_id,
        "title": doc.title,
        "content_versions": content_versions,
        "total_versions": len(content_versions),
    }
