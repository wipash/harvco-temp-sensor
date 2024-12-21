"""
Dependencies module for FastAPI application.

This module provides dependency functions for:
- Database sessions
- User authentication
- Authorization checks
- Pagination parameters
"""

from typing import AsyncGenerator, Optional
from datetime import datetime

from fastapi import Depends, HTTPException, status, Query
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
import jwt

from app.db import get_session
from app.core import security
from app.core.config import settings
from app.crud import crud_user
from app.models.user import User

# OAuth2 scheme for token authentication
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_STR}/auth/login"
)

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency that provides an async database session.

    Yields:
        AsyncSession: Database session
    """
    async for session in get_session():
        yield session

async def get_current_user(
    db: AsyncSession = Depends(get_db),
    token: str = Depends(oauth2_scheme)
) -> User:
    """
    Dependency that returns the current authenticated user.

    Args:
        db: Database session
        token: JWT token from request

    Returns:
        User: Current authenticated user

    Raises:
        HTTPException: If authentication fails
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = security.decode_token(token)
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except jwt.PyJWTError:
        raise credentials_exception

    user = await crud_user.get(db, id=int(user_id))
    if user is None:
        raise credentials_exception

    return user

async def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """
    Dependency that ensures the current user is active.

    Args:
        current_user: Current authenticated user

    Returns:
        User: Current active user

    Raises:
        HTTPException: If user is inactive
    """
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )
    return current_user

async def get_current_superuser(
    current_user: User = Depends(get_current_user),
) -> User:
    """
    Dependency that ensures the current user is a superuser.

    Args:
        current_user: Current authenticated user

    Returns:
        User: Current superuser

    Raises:
        HTTPException: If user is not a superuser
    """
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="The user doesn't have enough privileges"
        )
    return current_user

class PaginationParams:
    """
    Pagination parameters for list endpoints.
    """
    def __init__(
        self,
        skip: int = Query(default=0, ge=0),
        limit: int = Query(default=100, ge=1, le=1000)
    ):
        self.skip = skip
        self.limit = limit

async def get_pagination(
    pagination: PaginationParams = Depends()
) -> PaginationParams:
    """
    Dependency that provides pagination parameters.

    Args:
        pagination: Pagination parameters from query

    Returns:
        PaginationParams: Validated pagination parameters
    """
    return pagination

class DateRangeParams:
    """
    Date range parameters for filtering by date.
    """
    def __init__(
        self,
        start_date: Optional[datetime] = Query(default=None),
        end_date: Optional[datetime] = Query(default=None)
    ):
        self.start_date = start_date
        self.end_date = end_date

        if self.start_date and self.end_date and self.start_date > self.end_date:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="start_date must be before end_date"
            )

async def get_date_range(
    date_range: DateRangeParams = Depends()
) -> DateRangeParams:
    """
    Dependency that provides date range parameters.

    Args:
        date_range: Date range parameters from query

    Returns:
        DateRangeParams: Validated date range parameters
    """
    return date_range

def check_device_owner(user: User, device_id: int) -> bool:
    """
    Helper function to check if a user owns a device.

    Args:
        user: User to check
        device_id: Device ID to check

    Returns:
        bool: True if user owns device, False otherwise
    """
    return any(device.id == device_id for device in user.devices)

async def get_owned_device(
    device_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> User:
    """
    Dependency that ensures the current user owns the requested device.

    Args:
        device_id: Device ID to check
        current_user: Current authenticated user
        db: Database session

    Returns:
        User: Current user if they own the device

    Raises:
        HTTPException: If user doesn't own the device
    """
    if not check_device_owner(current_user, device_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions to access this device"
        )
    return current_user
