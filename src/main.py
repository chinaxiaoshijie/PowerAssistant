"""管理助手 - Malong Technologies Management Assistant.

FastAPI main application entry point.
"""

from pathlib import Path

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from src.api.v1.dashboard import router as dashboard_router
from src.api.v1.documents import router as docs_router
from src.api.v1.health import router as health_router
from src.api.v1.organization import router as org_router
from src.api.v1.sync import router as sync_router
from src.api.v1.metrics import router as metrics_router
from src.config.settings import settings
from src.database import database

logger = structlog.get_logger()

# Get the project root directory
PROJECT_ROOT = Path(__file__).parent.parent
STATIC_DIR = PROJECT_ROOT / "static"


def create_app() -> FastAPI:
    """Create and configure FastAPI application.

    Returns:
        Configured FastAPI application instance
    """
    app = FastAPI(
        title=settings.name,
        description="码隆科技研发与交付管理决策引擎",
        version=settings.version,
        docs_url="/api/docs" if settings.environment == "development" else None,
        redoc_url="/api/redoc" if settings.environment == "development" else None,
    )

    # Configure CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Configure appropriately for production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include routers
    app.include_router(health_router, prefix="/api/v1")
    app.include_router(org_router, prefix="/api/v1")
    app.include_router(sync_router, prefix="/api/v1")
    app.include_router(docs_router, prefix="/api/v1")
    app.include_router(dashboard_router, prefix="/api/v1")
    app.include_router(metrics_router, prefix="/api/v1")

    # Mount static files
    if STATIC_DIR.exists():
        app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
        logger.info("static_files_mounted", directory=str(STATIC_DIR))

    @app.on_event("startup")
    async def startup_event():
        """Application startup handler."""
        logger.info(
            "application_startup",
            app_name=settings.name,
            version=settings.version,
            environment=settings.environment,
        )

        # Initialize database connection
        database.initialize()
        logger.info("database_initialized")

    @app.on_event("shutdown")
    async def shutdown_event():
        """Application shutdown handler."""
        logger.info("application_shutdown")

    @app.get("/")
    async def root():
        """Root endpoint - redirect to dashboard."""
        return {
            "name": settings.name,
            "version": settings.version,
            "environment": settings.environment,
            "dashboard": "/dashboard",
            "docs": "/api/docs" if settings.environment == "development" else None,
        }

    @app.get("/dashboard", response_class=HTMLResponse)
    async def dashboard():
        """Serve the dashboard HTML page."""
        dashboard_file = STATIC_DIR / "dashboard" / "index.html"
        if dashboard_file.exists():
            with open(dashboard_file, "r", encoding="utf-8") as f:
                return f.read()
        return HTMLResponse(content="<h1>Dashboard not found</h1>", status_code=404)

    @app.get("/api")
    async def api_info():
        """API information endpoint."""
        return {
            "name": settings.name,
            "version": settings.version,
            "endpoints": {
                "health": "/api/v1/health",
                "organization": "/api/v1/organization",
                "sync": "/api/v1/sync",
            },
        }

    return app


# Create application instance
app = create_app()

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "src.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.environment == "development",
    )
