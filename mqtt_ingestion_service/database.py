from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from config import settings
from shared.models import Base


engine = create_async_engine(
    settings.DATABASE_URL,
    echo=True  # Set to True for SQLAlchemy logging
)

async_session_maker = sessionmaker(
    bind=engine,
    expire_on_commit=False,
    class_=AsyncSession
)

async def get_async_session() -> AsyncSession:
    async with async_session_maker() as session:
        yield session
