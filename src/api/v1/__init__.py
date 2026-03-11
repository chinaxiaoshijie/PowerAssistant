"""API v1 routes."""

from src.api.v1.documents import router as documents_router
from src.api.v1.health import router as health_router
from src.api.v1.organization import router as organization_router
from src.api.v1.sync import router as sync_router

__all__ = [
    "documents_router",
    "health_router",
    "organization_router",
    "sync_router",
]
