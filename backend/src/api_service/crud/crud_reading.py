"""
CRUD operations for Reading model.

This module implements Create, Read, Update, Delete operations for sensor readings using
the repository pattern.
"""

import logging
from typing import Optional, List, Any
from datetime import datetime, timedelta
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException

from models.reading import Reading, ReadingType
from schemas.reading import ReadingCreate, ReadingUpdate
from api_service.crud.base import CRUDBase
from api_service.crud.crud_device import device as crud_device
from models.device import Device


class CRUDReading(CRUDBase[Reading, ReadingCreate, ReadingUpdate]):
    """
    CRUD operations for Reading model.
    Inherits basic CRUD operations from CRUDBase.
    """

    async def _apply_device_offset(
        self, db: AsyncSession, reading: Reading, device: Optional[Device] = None
    ) -> Reading:
        """Apply device offset to a reading."""
        if device is None:
            device = await crud_device.get(db, id=reading.device_id)

        if device:
            if reading.reading_type == ReadingType.TEMPERATURE:
                offset = device.temperature_offset or 0.0  # Convert None to 0.0
                reading.value += offset
            elif reading.reading_type == ReadingType.HUMIDITY:
                offset = device.humidity_offset or 0.0  # Convert None to 0.0
                reading.value += offset

        return reading

    def _valid_value_filters(self):
        """Return SQLAlchemy filters for valid numeric values."""
        return and_(
            Reading.value.isnot(None),
            Reading.value != float("inf"),  # Check for positive infinity
            Reading.value != float("-inf"),  # Check for negative infinity
            Reading.value == Reading.value,  # PostgreSQL's way of checking for NaN
            # NaN is the only value where x != x
        )

    async def create_with_device(
        self, db: AsyncSession, *, obj_in: ReadingCreate, device_id: int
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
            timestamp=obj_in.timestamp or datetime.utcnow(),
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
        threshold: int = 500,  # Maximum number of readings before averaging
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
        conditions = [Reading.device_id == device_id, self._valid_value_filters()]

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

        # Apply offsets to all readings
        if readings:
            device = await crud_device.get(db, id=device_id)
            for reading in readings:
                await self._apply_device_offset(db, reading, device)

        logger = logging.getLogger(__name__)
        logger.info(
            f"Query executed for device_id={device_id}, reading_type={reading_type}"
        )
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
                    end_date,
                )

                window_readings = [
                    r
                    for r in type_readings
                    if current_window_start <= r.timestamp < current_window_end
                ]

                if window_readings:
                    avg_value = sum(r.value for r in window_readings) / len(
                        window_readings
                    )
                    mid_timestamp = window_readings[len(window_readings) // 2].timestamp

                    logger.info(
                        f"Window {current_window_start} to {current_window_end}: "
                        f"{len(window_readings)} readings, avg={avg_value}"
                    )

                    averaged_readings.append(
                        Reading(
                            device_id=device_id,
                            timestamp=mid_timestamp,
                            value=avg_value,
                            reading_type=window_readings[
                                0
                            ].reading_type,  # Use the reading type from the group
                        )
                    )

                current_window_start = current_window_end

        logger.info(f"Created {len(averaged_readings)} averaged readings")
        return averaged_readings

    async def get_latest_by_device(
        self,
        db: AsyncSession,
        *,
        device_id: int,
        reading_type: Optional[ReadingType] = None,
    ) -> Optional[Reading]:
        """
        Get the latest reading for a device with offset applied.

        Args:
            db: Database session
            device_id: Device ID
            reading_type: Optional reading type filter

        Returns:
            Optional[Reading]: Latest reading or None
        """
        query = select(Reading).where(
            and_(Reading.device_id == device_id, self._valid_value_filters())
        )

        if reading_type:
            query = query.where(Reading.reading_type == reading_type)

        query = query.order_by(Reading.timestamp.desc()).limit(1)
        result = await db.execute(query)
        reading = result.scalar_one_or_none()

        if reading:
            reading = await self._apply_device_offset(db, reading)

        return reading

    async def get_statistics(
        self,
        db: AsyncSession,
        *,
        device_id: int,
        reading_type: ReadingType,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> dict[str, float]:
        """
        Get statistics for readings of a device.
        """
        # Get device first to determine offset
        device = await crud_device.get(db, id=device_id)
        offset = 0.0
        if device:
            offset = (
                device.temperature_offset
                if reading_type == ReadingType.TEMPERATURE
                else device.humidity_offset
            ) or 0.0

        # Build query for statistics
        query = select(
            func.min(Reading.value).label("min"),
            func.max(Reading.value).label("max"),
            func.avg(Reading.value).label("avg"),
            func.count(Reading.id).label("count"),
        ).where(
            and_(
                Reading.device_id == device_id,
                Reading.reading_type == reading_type,
                self._valid_value_filters()
            )
        )

        if start_date:
            query = query.where(Reading.timestamp >= start_date)
        if end_date:
            query = query.where(Reading.timestamp <= end_date)

        result = await db.execute(query)
        stats = result.one()

        # Convert values, applying offset to non-null values
        def safe_float_with_offset(value: Any) -> float:
            if value is None:
                return 0.0
            try:
                float_val = float(value)
                if float_val != float_val:  # NaN check
                    return 0.0
                return float_val + offset
            except (ValueError, TypeError):
                return 0.0

        return {
            "min": safe_float_with_offset(stats.min),
            "max": safe_float_with_offset(stats.max),
            "avg": safe_float_with_offset(stats.avg),
            "count": int(stats.count),
        }

    async def get_readings_by_type(
        self,
        db: AsyncSession,
        *,
        reading_type: ReadingType,
        skip: int = 0,
        limit: int = 100,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
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
            and_(Reading.reading_type == reading_type, self._valid_value_filters())
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
        end_date: Optional[datetime] = None,
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
                func.count(Reading.value).label("count"),
            )
            .where(
                and_(Reading.reading_type == reading_type, self._valid_value_filters())
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
