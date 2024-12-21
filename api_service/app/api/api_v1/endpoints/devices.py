"""
Device endpoints for device management.

This module provides endpoints for device registration and management.
"""

from typing import List, Annotated, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import (
    get_db,
    get_current_active_user,
    get_current_superuser,
    get_pagination,
    get_date_range,
    PaginationParams,
    DateRangeParams
)
from app.crud import device as crud_device
from app.models.user import User
from app.models.reading import ReadingType
from app.schemas.device import DeviceCreate, DeviceUpdate, DeviceOut

router = APIRouter()

@router.post("", response_model=DeviceOut, status_code=status.HTTP_201_CREATED)
async def create_device(
    *,
    db: Annotated[AsyncSession, Depends(get_db)],
    device_in: DeviceCreate,
    current_user: Annotated[User, Depends(get_current_active_user)]
) -> DeviceOut:
    """
    Create new device.
    
    Args:
        db: Database session
        device_in: Device creation data
        current_user: Current authenticated user
        
    Returns:
        DeviceOut: Created device
        
    Raises:
        HTTPException: If device with this device_id already exists
    """
    device = await crud_device.get_by_device_id(db, device_id=device_in.device_id)
    if device:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Device with this device_id already exists"
        )
    device = await crud_device.create_with_owner(
        db,
        obj_in=device_in,
        owner_id=current_user.id
    )
    return device

@router.get("", response_model=List[DeviceOut])
async def read_devices(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_active_user)],
    pagination: Annotated[PaginationParams, Depends(get_pagination)],
    include_inactive: bool = Query(False, description="Include inactive devices")
) -> List[DeviceOut]:
    """
    Retrieve current user's devices.
    
    Args:
        db: Database session
        current_user: Current authenticated user
        pagination: Pagination parameters
        include_inactive: Whether to include inactive devices
        
    Returns:
        List[DeviceOut]: List of devices
    """
    devices = await crud_device.get_multi_by_owner_with_filters(
        db,
        owner_id=current_user.id,
        skip=pagination.skip,
        limit=pagination.limit,
        active_only=not include_inactive
    )
    return devices

@router.get("/stats")
async def read_devices_with_stats(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_active_user)],
    pagination: Annotated[PaginationParams, Depends(get_pagination)],
    include_inactive: bool = Query(False, description="Include inactive devices")
) -> List[dict]:
    """
    Retrieve devices with their statistics.
    
    Args:
        db: Database session
        current_user: Current authenticated user
        pagination: Pagination parameters
        include_inactive: Whether to include inactive devices
        
    Returns:
        List[dict]: List of devices with their statistics
    """
    return await crud_device.get_multi_by_owner_with_stats(
        db,
        owner_id=current_user.id,
        skip=pagination.skip,
        limit=pagination.limit,
        include_inactive=include_inactive
    )

@router.get("/{device_id}", response_model=DeviceOut)
async def read_device(
    device_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_active_user)]
) -> DeviceOut:
    """
    Get device by ID.
    
    Args:
        device_id: Device ID
        db: Database session
        current_user: Current authenticated user
        
    Returns:
        DeviceOut: Device information
        
    Raises:
        HTTPException: If device not found or user doesn't own it
    """
    device = await crud_device.get(db, id=device_id)
    if not device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Device not found"
        )
    if not await crud_device.is_owner(db, device_id=device_id, user_id=current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    return device

@router.get("/{device_id}/stats")
async def read_device_stats(
    device_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_active_user)],
    date_range: Annotated[DateRangeParams, Depends(get_date_range)],
    reading_type: Optional[ReadingType] = None
) -> dict:
    """
    Get device statistics.
    
    Args:
        device_id: Device ID
        db: Database session
        current_user: Current authenticated user
        date_range: Date range for statistics
        reading_type: Optional reading type filter
        
    Returns:
        dict: Device statistics
        
    Raises:
        HTTPException: If device not found or user doesn't own it
    """
    if not await crud_device.is_owner(db, device_id=device_id, user_id=current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    return await crud_device.get_device_stats(
        db,
        device_id=device_id,
        reading_type=reading_type,
        start_date=date_range.start_date,
        end_date=date_range.end_date
    )

@router.put("/{device_id}", response_model=DeviceOut)
async def update_device(
    device_id: int,
    device_in: DeviceUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_active_user)]
) -> DeviceOut:
    """
    Update device.
    
    Args:
        device_id: Device ID to update
        device_in: Update data
        db: Database session
        current_user: Current authenticated user
        
    Returns:
        DeviceOut: Updated device
        
    Raises:
        HTTPException: If device not found or user doesn't own it
    """
    device = await crud_device.get(db, id=device_id)
    if not device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Device not found"
        )
    if not await crud_device.is_owner(db, device_id=device_id, user_id=current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    device = await crud_device.update(db, db_obj=device, obj_in=device_in)
    return device

@router.delete("/{device_id}", response_model=DeviceOut)
async def delete_device(
    device_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_active_user)]
) -> DeviceOut:
    """
    Deactivate device.
    
    Args:
        device_id: Device ID to deactivate
        db: Database session
        current_user: Current authenticated user
        
    Returns:
        DeviceOut: Deactivated device
        
    Raises:
        HTTPException: If device not found or user doesn't own it
    """
    device = await crud_device.get(db, id=device_id)
    if not device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Device not found"
        )
    if not await crud_device.is_owner(db, device_id=device_id, user_id=current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    device = await crud_device.deactivate(db, id=device_id)
    return device

@router.post("/bulk-update-status", response_model=List[DeviceOut])
async def bulk_update_device_status(
    device_ids: List[int],
    is_active: bool,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_superuser)]
) -> List[DeviceOut]:
    """
    Bulk update device status. Superuser only.
    
    Args:
        device_ids: List of device IDs to update
        is_active: New active status
        db: Database session
        current_user: Current authenticated superuser
        
    Returns:
        List[DeviceOut]: List of updated devices
    """
    return await crud_device.bulk_update_status(
        db,
        device_ids=device_ids,
        is_active=is_active
    )
