import pytest
import pytest_asyncio
from datetime import datetime, timedelta
import uuid
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.crud_token import crud_refresh_token
from app.schemas.token import RefreshTokenCreate
from app.models.token import RefreshToken

@pytest.fixture
def refresh_token_create_data():
    """Sample refresh token creation data."""
    return {
        "token_id": str(uuid.uuid4()),
        "user_id": 1,
        "expires_at": datetime.utcnow() + timedelta(days=30)
    }

@pytest_asyncio.fixture
async def test_refresh_token(
    db_session: AsyncSession,
    test_user,
    refresh_token_create_data
) -> RefreshToken:
    """Create a test refresh token."""
    refresh_token_create_data["user_id"] = test_user.id
    token_in = RefreshTokenCreate(**refresh_token_create_data)
    return await crud_refresh_token.create(db_session, obj_in=token_in)

class TestCRUDRefreshToken:
    async def test_create_refresh_token(
        self,
        db_session: AsyncSession,
        test_user,
        refresh_token_create_data
    ):
        """Test creating a refresh token."""
        refresh_token_create_data["user_id"] = test_user.id
        token_in = RefreshTokenCreate(**refresh_token_create_data)
        token = await crud_refresh_token.create(db_session, obj_in=token_in)

        assert token.token_id == refresh_token_create_data["token_id"]
        assert token.user_id == test_user.id
        assert isinstance(token.created_at, datetime)
        assert token.expires_at == refresh_token_create_data["expires_at"]

    async def test_get_by_token_id(
        self,
        db_session: AsyncSession,
        test_refresh_token: RefreshToken
    ):
        """Test retrieving a refresh token by token_id."""
        token = await crud_refresh_token.get_by_token_id(
            db_session,
            token_id=test_refresh_token.token_id
        )
        assert token is not None
        assert token.id == test_refresh_token.id
        assert token.token_id == test_refresh_token.token_id

    async def test_get_active_by_user_id(
        self,
        db_session: AsyncSession,
        test_user,
        refresh_token_create_data
    ):
        """Test retrieving active refresh tokens for a user."""
        # Create two tokens - one active, one expired
        active_data = refresh_token_create_data.copy()
        active_data["user_id"] = test_user.id
        active_data["token_id"] = str(uuid.uuid4())
        active_token = RefreshTokenCreate(**active_data)
        await crud_refresh_token.create(db_session, obj_in=active_token)

        expired_data = refresh_token_create_data.copy()
        expired_data["user_id"] = test_user.id
        expired_data["token_id"] = str(uuid.uuid4())
        expired_data["expires_at"] = datetime.utcnow() - timedelta(days=1)
        expired_token = RefreshTokenCreate(**expired_data)
        await crud_refresh_token.create(db_session, obj_in=expired_token)

        # Get active tokens
        active_tokens = await crud_refresh_token.get_active_by_user_id(
            db_session,
            user_id=test_user.id
        )

        assert len(active_tokens) == 1
        assert active_tokens[0].token_id == active_data["token_id"]

    async def test_invalidate_token(
        self,
        db_session: AsyncSession,
        test_refresh_token: RefreshToken
    ):
        """Test invalidating a refresh token."""
        # Verify token exists
        token = await crud_refresh_token.get_by_token_id(
            db_session,
            token_id=test_refresh_token.token_id
        )
        assert token is not None

        # Invalidate token
        result = await crud_refresh_token.invalidate_token(
            db_session,
            token_id=test_refresh_token.token_id
        )
        assert result is True

        # Verify token no longer exists
        token = await crud_refresh_token.get_by_token_id(
            db_session,
            token_id=test_refresh_token.token_id
        )
        assert token is None

    async def test_cleanup_expired(
        self,
        db_session: AsyncSession,
        test_user,
        refresh_token_create_data
    ):
        """Test cleaning up expired refresh tokens."""
        # Create multiple tokens with different expiration times
        tokens_data = []
        # 2 expired tokens
        for _ in range(2):
            data = refresh_token_create_data.copy()
            data["user_id"] = test_user.id
            data["token_id"] = str(uuid.uuid4())
            data["expires_at"] = datetime.utcnow() - timedelta(days=1)
            tokens_data.append(data)
        
        # 1 active token
        active_data = refresh_token_create_data.copy()
        active_data["user_id"] = test_user.id
        active_data["token_id"] = str(uuid.uuid4())
        active_data["expires_at"] = datetime.utcnow() + timedelta(days=30)
        tokens_data.append(active_data)

        # Create all tokens
        for token_data in tokens_data:
            token_in = RefreshTokenCreate(**token_data)
            await crud_refresh_token.create(db_session, obj_in=token_in)

        # Run cleanup
        deleted_count = await crud_refresh_token.cleanup_expired(db_session)
        assert deleted_count == 2

        # Verify only active token remains
        remaining_tokens = await crud_refresh_token.get_active_by_user_id(
            db_session,
            user_id=test_user.id
        )
        assert len(remaining_tokens) == 1
        assert remaining_tokens[0].token_id == active_data["token_id"]
