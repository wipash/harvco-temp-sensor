from typing import AsyncGenerator

# Third-party imports
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

# Local application imports
from config import settings
from shared.models import Base


engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.SQLALCHEMY_ECHO,
    pool_size=20,         # Optional: adjust based on your needs
    max_overflow=0        # Optional: adjust based on your needs
)

async_session_maker = sessionmaker(
    bind=engine,
    expire_on_commit=False,
    class_=AsyncSession
)

async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """Asynchronous generator that provides a database session.

    Yields:
        AsyncSession: An async database session.
    """
    async with async_session_maker() as session:
        try:
            yield session
        finally:
            await session.close()
