import asyncio
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from typing import AsyncGenerator, Generator
from unittest.mock import patch

from app.db.base import Base
from app.core.config import Settings, settings

# Test database URL for SQLite
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

# Mock settings for testing
TEST_SETTINGS = {
    "DATABASE_URL": TEST_DATABASE_URL,
    "MQTT_BROKER_URL": "mqtt://localhost:1883",
    "SECRET_KEY": "test_secret_key",
    "API_V1_STR": "/api/v1",
    "ACCESS_TOKEN_EXPIRE_MINUTES": 60,
    "BACKEND_CORS_ORIGINS": ["http://localhost:3000"],
    "SQLALCHEMY_ECHO": False
}

@pytest.fixture(scope="session", autouse=True)
def mock_settings():
    """Override settings for testing."""
    with patch.object(settings, "DATABASE_URL", TEST_DATABASE_URL):
        with patch.object(settings, "MQTT_BROKER_URL", "mqtt://localhost:1883"):
            yield settings

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
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    yield engine
    
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
        yield session
        await session.rollback()

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
