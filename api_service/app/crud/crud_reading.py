"""
CRUD operations for Reading model.

This module implements Create, Read, Update, Delete operations for sensor readings using
the repository pattern.
"""

import logging
from typing import Optional, List, Any
from datetime import datetime, timedelta
from sqlalchemy import select, func, and_, not_
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException

from app.models.reading import Reading, ReadingType
from app.schemas.reading import ReadingCreate, ReadingUpdate
from app.crud.base import CRUDBase

class CRUDReading(CRUDBase[Reading, ReadingCreate, ReadingUpdate]):
    """
    CRUD operations for Reading model.
    Inherits basic CRUD operations from CRUDBase.
    """

    def _valid_value_filters(self):
        """Return SQLAlchemy filters for valid numeric values."""
        return and_(
            Reading.value.isnot(None),
            Reading.value != float('inf'),  # Check for positive infinity
            Reading.value != float('-inf'),  # Check for negative infinity
            Reading.value == Reading.value  # PostgreSQL's way of checking for NaN
                                          # NaN is the only value where x != x
        )

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
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        reading_type: Optional[ReadingType] = None,
        threshold: int = 500  # Maximum number of readings before averaging
    ) -> List[Reading]:
        """
        Get readings for a specific device with filters.

        Args:
            db: Database session
            device_id: Device ID
            start_date: Filter readings after this date
            end_date: Filter readings before this date
            reading_type: Optional reading type filter
            threshold: Maximum number of readings before averaging

        Returns:
            List[Reading]: List of readings
        """
        max_time_window = timedelta(days=30)
        if start_date and end_date and (end_date - start_date > max_time_window):
            raise HTTPException(status_code=400, detail="Time window too large")

        # Build base query with required filters
        conditions = [
            Reading.device_id == device_id,
            self._valid_value_filters()
        ]
        
        # Add reading_type filter if provided
        if reading_type is not None:
            conditions.append(Reading.reading_type == reading_type.value)

        query = select(Reading).where(and_(*conditions))

        if start_date:
            query = query.where(Reading.timestamp >= start_date)
        if end_date:
            query = query.where(Reading.timestamp <= end_date)

        query = query.order_by(Reading.timestamp.asc())

        result = await db.execute(query)
        readings = list(result.scalars().all())

        logger = logging.getLogger(__name__)
        logger.info(f"Query executed for device_id={device_id}, reading_type={reading_type}")
        logger.info(f"Time range: {start_date} to {end_date}")
        logger.info(f"Found {len(readings)} readings")

        if not readings:
            logger.info("No readings found, returning empty list")
            return []

        # If under threshold, return all readings
        if len(readings) <= threshold:
            logger.info(f"Under threshold ({threshold}), returning all readings")
            return readings

        # Group readings by type for averaging
        readings_by_type = {}
        for reading in readings:
            if reading.reading_type not in readings_by_type:
                readings_by_type[reading.reading_type] = []
            readings_by_type[reading.reading_type].append(reading)

        averaged_readings = []
        time_window = (end_date - start_date).total_seconds()
        sampling_window_size = time_window / threshold

        # Average each reading type separately
        for type_readings in readings_by_type.values():
            current_window_start = start_date
            while current_window_start < end_date:
                current_window_end = min(
                    current_window_start + timedelta(seconds=sampling_window_size),
                    end_date
                )
                
                window_readings = [
                    r for r in type_readings 
                    if current_window_start <= r.timestamp < current_window_end
                ]
                
                if window_readings:
                    avg_value = sum(r.value for r in window_readings) / len(window_readings)
                    mid_timestamp = window_readings[len(window_readings)//2].timestamp
                    
                    logger.info(f"Window {current_window_start} to {current_window_end}: "
                              f"{len(window_readings)} readings, avg={avg_value}")
                    
                    averaged_readings.append(Reading(
                        device_id=device_id,
                        timestamp=mid_timestamp,
                        value=avg_value,
                        reading_type=window_readings[0].reading_type  # Use the reading type from the group
                    ))
                
                current_window_start = current_window_end

        logger.info(f"Created {len(averaged_readings)} averaged readings")
        return averaged_readings

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
            .where(
                and_(
                    Reading.device_id == device_id,
                    self._valid_value_filters()
                )
            )
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
        import logging
        logger = logging.getLogger(__name__)

        # Filter out NaN values using a WHERE clause
        query = select(
            func.min(Reading.value).label("min"),
            func.max(Reading.value).label("max"),
            func.avg(Reading.value).label("avg"),
            func.count(Reading.id).label("count")
        ).where(
            and_(
                Reading.device_id == device_id,
                Reading.reading_type == reading_type,
                Reading.value != float('nan'),  # Exclude NaN values
                Reading.value.isnot(None)  # Exclude NULL values
            )
        )

        if start_date:
            query = query.where(Reading.timestamp >= start_date)
        if end_date:
            query = query.where(Reading.timestamp <= end_date)

        result = await db.execute(query)
        stats = result.one()

        logger.debug(f"Raw stats from database: min={stats.min}, max={stats.max}, avg={stats.avg}, count={stats.count}")

        # Convert values, defaulting to None instead of 0.0 if no valid readings
        def safe_float(value: Any) -> Optional[float]:
            if value is None:
                return None
            try:
                float_val = float(value)
                if float_val != float_val:  # NaN check
                    return None
                return float_val
            except (ValueError, TypeError):
                return None

        min_val = safe_float(stats.min)
        max_val = safe_float(stats.max)
        avg_val = safe_float(stats.avg)

        # Only use 0.0 as fallback if we actually have no valid readings
        result = {
            "min": min_val if min_val is not None else 0.0,
            "max": max_val if max_val is not None else 0.0,
            "avg": avg_val if avg_val is not None else 0.0,
            "count": int(stats.count)
        }

        logger.debug(f"Final result: {result}")
        return result

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
        query = select(Reading).where(
            and_(
                Reading.reading_type == reading_type,
                self._valid_value_filters()
            )
        )

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
                func.avg(Reading.value).label("average"),
                func.count(Reading.value).label("count")
            )
            .where(
                and_(
                    Reading.reading_type == reading_type,
                    self._valid_value_filters()
                )
            )
            .group_by(Reading.device_id)
            .having(func.count(Reading.value) > 0)  # Only include devices with readings
        )

        if start_date:
            query = query.where(Reading.timestamp >= start_date)
        if end_date:
            query = query.where(Reading.timestamp <= end_date)

        result = await db.execute(query)
        rows = result.all()

        # Convert to list of tuples, handling NULL averages
        return [
            (r.device_id, float(r.average) if r.average is not None else 0.0)
            for r in rows
        ]

# Create singleton instance for use across the application
reading = CRUDReading(Reading)
