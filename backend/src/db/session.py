"""
Database session and engine configuration.

This module sets up the SQLAlchemy engine and session factory for async database operations.
"""

from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import (
    create_async_engine,
    AsyncSession,
    async_sessionmaker,
)

from backend.src.config import settings

# Create async engine
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.SQLALCHEMY_ECHO,
    pool_pre_ping=True,
    pool_size=20,
    max_overflow=10,
    pool_recycle=3600,
)

# Create async session factory
AsyncSessionFactory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

async def get_session() -> AsyncIterator[AsyncSession]:
    """
    Get a database session.

    Yields:
        AsyncSession: Database session

    Usage:
        async with get_session() as session:
            # Use session here
    """
    async with AsyncSessionFactory() as session:
        try:
            yield session
        finally:
            await session.close()

async def init_db() -> None:
    """
    Initialize database connection.

    This function can be used to verify database connection on startup
    and perform any necessary initialization.
    """
    try:
        async with engine.begin() as conn:
            await conn.run_sync(lambda _: None)
    except Exception as e:
        raise Exception(f"Failed to initialize database: {str(e)}")

async def close_db() -> None:
    """
    Close database connections.

    This function should be called when shutting down the application
    to ensure all connections are properly closed.
    """
    await engine.dispose()

# Optional: Function to create all tables
async def create_tables() -> None:
    """
    Create all database tables.

    This function should only be used for development/testing.
    Production should use proper migrations.
    """
    from models.base import Base

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def cleanup_database():
    """Cleanup database connections when shutting down."""
    await engine.dispose()
