"""
Reading endpoints for sensor reading retrieval.

This module provides endpoints for retrieving sensor readings.
"""

from typing import List, Annotated, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from models.device import Device
from models.reading import Reading

from api_service.api.deps import (
    get_db,
    get_current_active_user,
    get_pagination,
    get_date_range,
    PaginationParams,
    DateRangeParams,
)
from api_service.crud import reading as crud_reading, device as crud_device
from models.user import User
from models.reading import ReadingType
from schemas.reading import ReadingOut, ReadingStatistics


async def apply_device_offsets(
    db: AsyncSession, readings: List[Reading]
) -> List[Reading]:
    """Apply device offsets to readings."""
    # Group readings by device to minimize database queries
    readings_by_device = {}
    for reading in readings:
        if reading.device_id not in readings_by_device:
            readings_by_device[reading.device_id] = []
        readings_by_device[reading.device_id].append(reading)

    # Get all needed devices in one query
    device_ids = list(readings_by_device.keys())
    devices = await db.execute(select(Device).where(Device.id.in_(device_ids)))
    devices = {d.id: d for d in devices.scalars().all()}

    # Apply offsets
    for device_id, device_readings in readings_by_device.items():
        device = devices.get(device_id)
        if device:
            for reading in device_readings:
                if reading.reading_type == ReadingType.TEMPERATURE:
                    # Use 0.0 if temperature_offset is None
                    offset = device.temperature_offset or 0.0
                    reading.value += offset
                elif reading.reading_type == ReadingType.HUMIDITY:
                    # Use 0.0 if humidity_offset is None
                    offset = device.humidity_offset or 0.0
                    reading.value += offset

    # Apply device offsets before returning
    readings = await apply_device_offsets(db, readings)
    return readings


router = APIRouter()


@router.get("", response_model=List[ReadingOut])
async def read_readings(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_active_user)],
    pagination: Annotated[PaginationParams, Depends(get_pagination)],
    date_range: Annotated[DateRangeParams, Depends(get_date_range)],
    device_id: Optional[int] = Query(None, description="Filter by device ID"),
    reading_type: Optional[ReadingType] = Query(
        None, description="Filter by reading type"
    ),
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
        if not await crud_device.is_owner(
            db, device_id=device_id, user_id=current_user.id
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not enough permissions to access this device",
            )
        readings = await crud_reading.get_by_device(
            db,
            device_id=device_id,
            start_date=date_range.start_date,
            end_date=date_range.end_date,
            reading_type=reading_type,
        )
    else:
        readings = await crud_reading.get_readings_by_type(
            db,
            reading_type=reading_type,
            skip=pagination.skip,
            limit=pagination.limit,
            start_date=date_range.start_date,
            end_date=date_range.end_date,
        )

    return readings


@router.get("/statistics", response_model=ReadingStatistics)
async def get_reading_statistics(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_active_user)],
    date_range: Annotated[DateRangeParams, Depends(get_date_range)],
    device_id: int = Query(..., description="Device ID"),
    reading_type: ReadingType = Query(..., description="Reading type"),
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
            detail="Not enough permissions to access this device",
        )

    # Get the device to access its offset
    device = await crud_device.get(db, id=device_id)
    if not device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Device not found"
        )

    stats = await crud_reading.get_statistics(
        db,
        device_id=device_id,
        reading_type=reading_type,
        start_date=date_range.start_date,
        end_date=date_range.end_date,
    )

    # Apply the appropriate offset to all statistics
    offset = 0.0  # Default to 0.0
    if device:
        if reading_type == ReadingType.TEMPERATURE:
            offset = device.temperature_offset or 0.0
        else:
            offset = device.humidity_offset or 0.0

    stats["min"] += offset
    stats["max"] += offset
    stats["avg"] += offset

    return stats


@router.get("/latest", response_model=ReadingOut)
async def get_latest_reading(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_active_user)],
    device_id: int = Query(..., description="Device ID"),
    reading_type: Optional[ReadingType] = Query(None, description="Reading type"),
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
            detail="Not enough permissions to access this device",
        )

    reading = await crud_reading.get_latest_by_device(
        db, device_id=device_id, reading_type=reading_type
    )

    if not reading:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No readings found for this device",
        )

    # Apply the device offset
    device = await crud_device.get(db, id=device_id)
    if device:
        if reading.reading_type == ReadingType.TEMPERATURE:
            offset = device.temperature_offset or 0.0
            reading.value += offset
        elif reading.reading_type == ReadingType.HUMIDITY:
            offset = device.humidity_offset or 0.0
            reading.value += offset

    return reading


@router.get("/device-averages", response_model=List[dict])
async def get_device_averages(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_active_user)],
    date_range: Annotated[DateRangeParams, Depends(get_date_range)],
    reading_type: ReadingType = Query(..., description="Reading type"),
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
    # First, get all the user's devices
    devices_query = select(Device).where(Device.owner_id == current_user.id)
    result = await db.execute(devices_query)
    user_devices = {device.id: device.device_id for device in result.scalars().all()}

    averages = await crud_reading.get_device_averages(
        db,
        reading_type=reading_type,
        start_date=date_range.start_date,
        end_date=date_range.end_date,
    )

    # Filter and format the response
    filtered_averages = [
        {
            "device_id": user_devices[device_id],  # Use the device_id string
            "internal_id": device_id,  # Include the internal ID
            "average": avg,
        }
        for device_id, avg in averages
        if device_id in user_devices
    ]

    return filtered_averages
