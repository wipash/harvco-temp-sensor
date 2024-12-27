import asyncio
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from typing import AsyncGenerator, Generator
from src.models.user import User

from src.models.base import Base
from src.config import settings

# Test database URL for SQLite
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

# Mock settings for testing
TEST_SETTINGS = {
    "DATABASE_URL": TEST_DATABASE_URL,
    "SECRET_KEY": "test_secret_key",
    "API_V1_STR": "/api/v1",
    "ACCESS_TOKEN_EXPIRE_MINUTES": 60,
    "BACKEND_CORS_ORIGINS": ["http://localhost:3000"],
    "SQLALCHEMY_ECHO": False,
    "LOG_LEVEL": "DEBUG"
}

@pytest.fixture(scope="session", autouse=True)
def mock_settings():
    """Override settings for testing."""
    # Apply all test settings at once
    for key, value in TEST_SETTINGS.items():
        setattr(settings, key, value)
    return settings

@pytest.fixture(scope="session")
def event_loop() -> Generator:
    """Create an instance of the default event loop for each test case."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest_asyncio.fixture(scope="session")
async def test_engine():
    """Create a test database engine."""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        echo=False,
        future=True
    )

    # Create tables once at the start of test session
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    # Clean up at the end of test session
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()

@pytest_asyncio.fixture
async def db_session(test_engine) -> AsyncGenerator[AsyncSession, None]:
    """Create a test database session."""
    async_session = sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False
    )

    async with async_session() as session:
        try:
            yield session
        finally:
            await session.rollback()
            # Clear data but don't drop tables
            for table in reversed(Base.metadata.sorted_tables):
                await session.execute(table.delete())
            await session.commit()

# Test data fixtures
@pytest.fixture
def user_create_data():
    """Sample user creation data."""
    return {
        "email": "test@example.com",
        "password": "testpassword123",
        "is_active": True,
        "is_superuser": False
    }

@pytest.fixture
def device_create_data():
    """Sample device creation data."""
    return {
        "device_id": "test-device-001",
        "name": "Test Device",
        "is_active": True
    }

@pytest.fixture
def reading_create_data():
    """Sample reading creation data."""
    return {
        "reading_type": "temperature",
        "value": 23.5,
        "device_id": "test-device-001"
    }

@pytest_asyncio.fixture
async def test_user(db_session: AsyncSession) -> User:
    """Create a test user."""
    from src.api_service.crud.crud_user import user as crud_user
    from src.schemas.user import UserCreate

    user_in = UserCreate(
        email="test@example.com",
        password="testpassword123",
        is_active=True,
        is_superuser=False
    )

    db_user = await crud_user.create(db_session, obj_in=user_in)
    return db_user
