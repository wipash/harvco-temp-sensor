from datetime import datetime
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from api_service.crud.base import CRUDBase
from models.token import RefreshToken
from schemas.token import RefreshTokenCreate, RefreshTokenDB


class CRUDRefreshToken(CRUDBase[RefreshToken, RefreshTokenCreate, RefreshTokenDB]):
    """CRUD operations for refresh tokens."""

    async def get_by_token_id(
        self, db: AsyncSession, *, token_id: str
    ) -> Optional[RefreshToken]:
        """
        Get refresh token by its unique token_id.

        Args:
            db: Database session
            token_id: Unique token identifier

        Returns:
            RefreshToken object if found, None otherwise
        """
        query = select(RefreshToken).where(RefreshToken.token_id == token_id)
        result = await db.execute(query)
        return result.scalar_one_or_none()

    async def get_active_by_user_id(
        self, db: AsyncSession, *, user_id: int
    ) -> list[RefreshToken]:
        """
        Get all active refresh tokens for a user.

        Args:
            db: Database session
            user_id: User ID to get tokens for

        Returns:
            List of active RefreshToken objects
        """
        query = select(RefreshToken).where(
            RefreshToken.user_id == user_id, RefreshToken.expires_at > datetime.utcnow()
        )
        result = await db.execute(query)
        return result.scalars().all()

    async def invalidate_token(self, db: AsyncSession, *, token_id: str) -> bool:
        """
        Invalidate a refresh token by deleting it.

        Args:
            db: Database session
            token_id: Token ID to invalidate

        Returns:
            True if token was found and deleted, False otherwise
        """
        token = await self.get_by_token_id(db, token_id=token_id)
        if token:
            await db.delete(token)
            await db.commit()
            return True
        return False

    async def cleanup_expired(self, db: AsyncSession) -> int:
        """
        Remove all expired refresh tokens from database.

        Args:
            db: Database session

        Returns:
            Number of tokens deleted
        """
        query = select(RefreshToken).where(RefreshToken.expires_at <= datetime.utcnow())
        result = await db.execute(query)
        expired_tokens = result.scalars().all()

        count = len(expired_tokens)
        for token in expired_tokens:
            await db.delete(token)

        await db.commit()
        return count


# Create CRUD instance
crud_refresh_token = CRUDRefreshToken(RefreshToken)
