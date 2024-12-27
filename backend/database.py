"""Database connection and session management for the MQTT Ingestion Service."""
from typing import AsyncGenerator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import (
    create_async_engine,
    AsyncSession,
    async_sessionmaker,
)

from config import settings

# Create async engine with configured settings
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.SQLALCHEMY_ECHO,
    pool_pre_ping=True,  # Enable connection health checks
    pool_size=20,        # Adjust based on expected concurrent connections
    max_overflow=0       # Prevent creation of additional connections beyond pool_size
)

# Create reusable async session factory
AsyncSessionFactory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False
)

@asynccontextmanager
async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """Get an async database session as a context manager.
    
    Yields:
        AsyncSession: Database session that will be automatically closed.
        
    Example:
        async with get_async_session() as session:
            result = await session.execute(query)
    """
    session = AsyncSessionFactory()
    try:
        yield session
    finally:
        await session.close()

async def cleanup_database():
    """Cleanup database connections when shutting down."""
    await engine.dispose()
