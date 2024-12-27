"""
User endpoints for user management.

This module provides endpoints for user registration and management.
"""

from typing import List, Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from api_service.api.deps import (
    get_db,
    get_current_active_user,
    get_current_superuser,
    get_pagination,
    PaginationParams
)
from api_service.crud import user as crud_user
from models.user import User
from schemas.user import UserCreate, UserOut, UserWithDevices
from schemas.device import DeviceOut

router = APIRouter()

@router.post("", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def create_user(
    *,
    db: Annotated[AsyncSession, Depends(get_db)],
    user_in: UserCreate,
) -> User:
    """
    Create new user.

    Args:
        db: Database session
        user_in: User creation data

    Returns:
        User: Created user

    Raises:
        HTTPException: If user with this email already exists
    """
    user = await crud_user.get_by_email(db, email=user_in.email)
    if user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User with this email already exists"
        )
    user = await crud_user.create(db, obj_in=user_in)
    return user

@router.get("/me", response_model=UserWithDevices)
async def read_user_me(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_active_user)]
) -> User:
    """
    Get current user.

    Args:
        db: Database session
        current_user: Current authenticated user

    Returns:
        User: Current user with their devices
    """
    # Explicitly load the devices relationship with all columns
    query = (
        select(User)
        .options(selectinload(User.devices))
        .where(User.id == current_user.id)
    )
    result = await db.execute(query)
    user = result.scalar_one()

    # Ensure devices have is_active set
    for device in user.devices:
        if device.is_active is None:
            device.is_active = True

    return user

@router.get("/me/devices", response_model=List[DeviceOut])
async def read_user_devices(
    *,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_active_user)],
    pagination: Annotated[PaginationParams, Depends(get_pagination)]
) -> List[DeviceOut]:
    """
    Get current user's devices.

    Args:
        db: Database session
        current_user: Current authenticated user
        pagination: Pagination parameters

    Returns:
        List[DeviceOut]: List of user's devices
    """
    devices = await crud_user.get_devices(
        db,
        user_id=current_user.id,
        skip=pagination.skip,
        limit=pagination.limit
    )
    return devices

@router.get("", response_model=List[UserOut])
async def read_users(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_superuser)],
    pagination: Annotated[PaginationParams, Depends(get_pagination)]
) -> List[User]:
    """
    Retrieve users. Only for superusers.

    Args:
        db: Database session
        current_user: Current authenticated superuser
        pagination: Pagination parameters

    Returns:
        List[User]: List of users
    """
    users = await crud_user.get_multi(
        db,
        skip=pagination.skip,
        limit=pagination.limit
    )
    return users

@router.get("/{user_id}", response_model=UserWithDevices)
async def read_user_by_id(
    user_id: int,
    current_user: Annotated[User, Depends(get_current_superuser)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> User:
    """
    Get user by ID. Only for superusers.

    Args:
        user_id: User ID
        current_user: Current authenticated superuser
        db: Database session

    Returns:
        User: User with their devices

    Raises:
        HTTPException: If user not found
    """
    user = await crud_user.get(db, id=user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    return user

@router.delete("/{user_id}", response_model=UserOut)
async def deactivate_user(
    user_id: int,
    current_user: Annotated[User, Depends(get_current_superuser)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> User:
    """
    Deactivate a user. Only for superusers.

    Args:
        user_id: User ID to deactivate
        current_user: Current authenticated superuser
        db: Database session

    Returns:
        User: Deactivated user

    Raises:
        HTTPException: If user not found
    """
    user = await crud_user.deactivate(db, user_id=user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    return user
