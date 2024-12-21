"""
CRUD operations for Reading model.

This module implements Create, Read, Update, Delete operations for sensor readings using
the repository pattern.
"""

from typing import Optional, List, Any
from datetime import datetime
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.reading import Reading, ReadingType
from app.schemas.reading import ReadingCreate, ReadingUpdate
from app.crud.base import CRUDBase

class CRUDReading(CRUDBase[Reading, ReadingCreate, ReadingUpdate]):
    """
    CRUD operations for Reading model.
    Inherits basic CRUD operations from CRUDBase.
    """

    async def create_with_device(
        self,
        db: AsyncSession,
        *,
        obj_in: ReadingCreate,
        device_id: int
    ) -> Reading:
        """
        Create a new reading for a device.

        Args:
            db: Database session
            obj_in: Reading creation data
            device_id: ID of the device

        Returns:
            Reading: Created reading
        """
        db_obj = Reading(
            device_id=device_id,
            reading_type=obj_in.reading_type,
            value=obj_in.value,
            timestamp=obj_in.timestamp or datetime.utcnow()
        )
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj

    async def get_by_device(
        self,
        db: AsyncSession,
        *,
        device_id: int,
        skip: int = 0,
        limit: int = 100,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        reading_type: Optional[ReadingType] = None
    ) -> List[Reading]:
        """
        Get readings for a specific device with filters.

        Args:
            db: Database session
            device_id: Device ID
            skip: Number of records to skip
            limit: Maximum number of records to return
            start_date: Filter readings after this date
            end_date: Filter readings before this date
            reading_type: Filter by reading type

        Returns:
            List[Reading]: List of readings
        """
        query = select(Reading).where(Reading.device_id == device_id)

        if start_date:
            query = query.where(Reading.timestamp >= start_date)
        if end_date:
            query = query.where(Reading.timestamp <= end_date)
        if reading_type:
            query = query.where(Reading.reading_type == reading_type)

        query = query.order_by(Reading.timestamp.desc()).offset(skip).limit(limit)
        result = await db.execute(query)
        return list(result.scalars().all())

    async def get_latest_by_device(
        self,
        db: AsyncSession,
        *,
        device_id: int,
        reading_type: Optional[ReadingType] = None
    ) -> Optional[Reading]:
        """
        Get the latest reading for a device.

        Args:
            db: Database session
            device_id: Device ID
            reading_type: Optional reading type filter

        Returns:
            Optional[Reading]: Latest reading or None
        """
        query = (
            select(Reading)
            .where(Reading.device_id == device_id)
        )
        
        if reading_type:
            query = query.where(Reading.reading_type == reading_type)
            
        query = query.order_by(Reading.timestamp.desc()).limit(1)
        result = await db.execute(query)
        return result.scalar_one_or_none()

    async def get_statistics(
        self,
        db: AsyncSession,
        *,
        device_id: int,
        reading_type: ReadingType,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> dict[str, float]:
        """
        Get statistics for readings of a device.

        Args:
            db: Database session
            device_id: Device ID
            reading_type: Type of reading
            start_date: Start date for statistics
            end_date: End date for statistics

        Returns:
            dict: Statistics including min, max, avg
        """
        query = select(
            func.min(Reading.value).label("min"),
            func.max(Reading.value).label("max"),
            func.avg(Reading.value).label("avg"),
            func.count(Reading.id).label("count")
        ).where(
            and_(
                Reading.device_id == device_id,
                Reading.reading_type == reading_type
            )
        )

        if start_date:
            query = query.where(Reading.timestamp >= start_date)
        if end_date:
            query = query.where(Reading.timestamp <= end_date)

        result = await db.execute(query)
        stats = result.one()
        
        return {
            "min": float(stats.min) if stats.min is not None else 0.0,
            "max": float(stats.max) if stats.max is not None else 0.0,
            "avg": float(stats.avg) if stats.avg is not None else 0.0,
            "count": int(stats.count)
        }

    async def get_readings_by_type(
        self,
        db: AsyncSession,
        *,
        reading_type: ReadingType,
        skip: int = 0,
        limit: int = 100,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[Reading]:
        """
        Get readings by type across all devices.

        Args:
            db: Database session
            reading_type: Type of reading
            skip: Number of records to skip
            limit: Maximum number of records to return
            start_date: Filter readings after this date
            end_date: Filter readings before this date

        Returns:
            List[Reading]: List of readings
        """
        query = select(Reading).where(Reading.reading_type == reading_type)

        if start_date:
            query = query.where(Reading.timestamp >= start_date)
        if end_date:
            query = query.where(Reading.timestamp <= end_date)

        query = query.order_by(Reading.timestamp.desc()).offset(skip).limit(limit)
        result = await db.execute(query)
        return list(result.scalars().all())

    async def get_device_averages(
        self,
        db: AsyncSession,
        *,
        reading_type: ReadingType,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[tuple[int, float]]:
        """
        Get average readings by device.

        Args:
            db: Database session
            reading_type: Type of reading
            start_date: Start date for average
            end_date: End date for average

        Returns:
            List[tuple]: List of (device_id, average) tuples
        """
        query = (
            select(
                Reading.device_id,
                func.avg(Reading.value).label("average")
            )
            .where(Reading.reading_type == reading_type)
            .group_by(Reading.device_id)
        )

        if start_date:
            query = query.where(Reading.timestamp >= start_date)
        if end_date:
            query = query.where(Reading.timestamp <= end_date)

        result = await db.execute(query)
        return [(r.device_id, float(r.average)) for r in result.all()]

# Create singleton instance for use across the application
reading = CRUDReading(Reading)
