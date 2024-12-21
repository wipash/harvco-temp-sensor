"""
Reading endpoints for sensor reading retrieval.

This module provides endpoints for retrieving sensor readings.
"""

from typing import List, Annotated, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import (
    get_db,
    get_current_active_user,
    get_pagination,
    get_date_range,
    PaginationParams,
    DateRangeParams
)
from app.crud import reading as crud_reading, device as crud_device
from app.models.user import User
from app.models.reading import ReadingType
from app.schemas.reading import ReadingOut, ReadingStatistics

router = APIRouter()

@router.get("", response_model=List[ReadingOut])
async def read_readings(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_active_user)],
    pagination: Annotated[PaginationParams, Depends(get_pagination)],
    date_range: Annotated[DateRangeParams, Depends(get_date_range)],
    device_id: Optional[int] = Query(None, description="Filter by device ID"),
    reading_type: Optional[ReadingType] = Query(None, description="Filter by reading type")
) -> List[ReadingOut]:
    """
    Retrieve readings with optional filters.
    
    Args:
        db: Database session
        current_user: Current authenticated user
        pagination: Pagination parameters
        date_range: Date range filter
        device_id: Optional device ID filter
        reading_type: Optional reading type filter
        
    Returns:
        List[ReadingOut]: List of readings
        
    Raises:
        HTTPException: If device_id is provided and user doesn't own the device
    """
    if device_id:
        if not await crud_device.is_owner(db, device_id=device_id, user_id=current_user.id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not enough permissions to access this device"
            )
        readings = await crud_reading.get_by_device(
            db,
            device_id=device_id,
            skip=pagination.skip,
            limit=pagination.limit,
            start_date=date_range.start_date,
            end_date=date_range.end_date,
            reading_type=reading_type
        )
    else:
        readings = await crud_reading.get_readings_by_type(
            db,
            reading_type=reading_type,
            skip=pagination.skip,
            limit=pagination.limit,
            start_date=date_range.start_date,
            end_date=date_range.end_date
        )
    
    return readings

@router.get("/statistics", response_model=ReadingStatistics)
async def get_reading_statistics(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_active_user)],
    date_range: Annotated[DateRangeParams, Depends(get_date_range)],
    device_id: int = Query(..., description="Device ID"),
    reading_type: ReadingType = Query(..., description="Reading type")
) -> ReadingStatistics:
    """
    Get statistics for readings from a specific device.
    
    Args:
        db: Database session
        current_user: Current authenticated user
        date_range: Date range for statistics
        device_id: Device ID
        reading_type: Reading type
        
    Returns:
        ReadingStatistics: Reading statistics
        
    Raises:
        HTTPException: If user doesn't own the device
    """
    if not await crud_device.is_owner(db, device_id=device_id, user_id=current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions to access this device"
        )
    
    stats = await crud_reading.get_statistics(
        db,
        device_id=device_id,
        reading_type=reading_type,
        start_date=date_range.start_date,
        end_date=date_range.end_date
    )
    return stats

@router.get("/latest", response_model=ReadingOut)
async def get_latest_reading(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_active_user)],
    device_id: int = Query(..., description="Device ID"),
    reading_type: Optional[ReadingType] = Query(None, description="Reading type")
) -> ReadingOut:
    """
    Get the latest reading from a specific device.
    
    Args:
        db: Database session
        current_user: Current authenticated user
        device_id: Device ID
        reading_type: Optional reading type filter
        
    Returns:
        ReadingOut: Latest reading
        
    Raises:
        HTTPException: If user doesn't own the device or no readings found
    """
    if not await crud_device.is_owner(db, device_id=device_id, user_id=current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions to access this device"
        )
    
    reading = await crud_reading.get_latest_by_device(
        db,
        device_id=device_id,
        reading_type=reading_type
    )
    
    if not reading:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No readings found for this device"
        )
    
    return reading

@router.get("/device-averages", response_model=List[dict])
async def get_device_averages(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_active_user)],
    date_range: Annotated[DateRangeParams, Depends(get_date_range)],
    reading_type: ReadingType = Query(..., description="Reading type")
) -> List[dict]:
    """
    Get average readings for all devices user has access to.
    
    Args:
        db: Database session
        current_user: Current authenticated user
        date_range: Date range for averages
        reading_type: Reading type
        
    Returns:
        List[dict]: List of device averages
    """
    averages = await crud_reading.get_device_averages(
        db,
        reading_type=reading_type,
        start_date=date_range.start_date,
        end_date=date_range.end_date
    )
    
    # Filter to only include devices owned by the user
    user_devices = set(device.id for device in current_user.devices)
    filtered_averages = [
        {"device_id": device_id, "average": avg}
        for device_id, avg in averages
        if device_id in user_devices
    ]
    
    return filtered_averages
