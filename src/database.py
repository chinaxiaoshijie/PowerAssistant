"""Database connection and session management."""

from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import declarative_base

from src.config.settings import settings

# Base class for SQLAlchemy models
Base = declarative_base()


class Database:
    """Database manager for async PostgreSQL operations."""

    def __init__(self) -> None:
        """Initialize database engine and session factory."""
        self._engine: AsyncEngine | None = None
        self._session_factory: async_sessionmaker[AsyncSession] | None = None

    def initialize(self) -> None:
        """Create async engine and session factory."""
        db_settings = settings.database

        self._engine = create_async_engine(
            db_settings.url,
            echo=db_settings.echo,
            pool_size=db_settings.pool_size,
            max_overflow=db_settings.max_overflow,
        )

        self._session_factory = async_sessionmaker(
            bind=self._engine,
            autocommit=False,
            autoflush=False,
            expire_on_commit=False,
        )

    async def close(self) -> None:
        """Close database engine and connections."""
        if self._engine:
            await self._engine.dispose()
            self._engine = None
            self._session_factory = None

    @property
    def engine(self) -> AsyncEngine:
        """Get the async database engine.

        Returns:
            AsyncEngine instance.

        Raises:
            RuntimeError: If database is not initialized.
        """
        if self._engine is None:
            raise RuntimeError("Database not initialized. Call initialize() first.")
        return self._engine

    @property
    def session_factory(self) -> async_sessionmaker[AsyncSession]:
        """Get the async session factory.

        Returns:
            async_sessionmaker for creating sessions.

        Raises:
            RuntimeError: If database is not initialized.
        """
        if self._session_factory is None:
            raise RuntimeError("Database not initialized. Call initialize() first.")
        return self._session_factory

    async def create_tables(self) -> None:
        """Create all tables defined in SQLAlchemy models."""
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    async def drop_tables(self) -> None:
        """Drop all tables defined in SQLAlchemy models."""
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)


# Global database instance
database = Database()


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Get database session for dependency injection.

    Yields:
        AsyncSession for database operations.

    Example:
        @app.get("/items")
        async def get_items(db: AsyncSession = Depends(get_db_session)):
            result = await db.execute(select(Item))
            return result.scalars().all()
    """
    if database.session_factory is None:
        raise RuntimeError("Database not initialized")

    async with database.session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
