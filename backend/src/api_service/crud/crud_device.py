"""
CRUD operations for Device model.

This module implements Create, Read, Update, Delete operations for devices using
the repository pattern.
"""

from typing import Optional, List
from datetime import datetime, timedelta
from sqlalchemy import select, func, and_
from models.reading import ReadingType
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from models.device import Device
from models.reading import Reading
from schemas.device import DeviceCreate, DeviceUpdate
from api_service.crud.base import CRUDBase


class CRUDDevice(CRUDBase[Device, DeviceCreate, DeviceUpdate]):
    """
    CRUD operations for Device model.
    Inherits basic CRUD operations from CRUDBase.
    """

    async def create_with_owner(
        self, db: AsyncSession, *, obj_in: DeviceCreate, owner_id: int
    ) -> Device:
        """
        Create a new device with an owner.

        Args:
            db: Database session
            obj_in: Device creation data
            owner_id: ID of the device owner

        Returns:
            Device: Created device
        """
        db_obj = Device(**obj_in.model_dump(exclude={"id"}), owner_id=owner_id)
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj

    async def get_by_device_id(
        self, db: AsyncSession, *, device_id: str
    ) -> Optional[Device]:
        """
        Get a device by its device_id.

        Args:
            db: Database session
            device_id: Device identifier

        Returns:
            Optional[Device]: Found device or None
        """
        query = select(Device).where(Device.device_id == device_id)
        result = await db.execute(query)
        return result.scalar_one_or_none()

    async def get_multi_by_owner_with_filters(
        self,
        db: AsyncSession,
        *,
        owner_id: int,
        skip: int = 0,
        limit: int = 100,
        active_only: bool = True,
        with_latest_reading: bool = False,
    ) -> List[Device]:
        """
        Get multiple devices belonging to an owner with filters.

        Args:
            db: Database session
            owner_id: ID of the owner
            skip: Number of records to skip
            limit: Maximum number of records to return
            active_only: If True, return only active devices
            with_latest_reading: If True, include latest reading

        Returns:
            List[Device]: List of devices
        """
        query = select(Device).where(Device.owner_id == owner_id)

        if active_only:
            query = query.where(Device.is_active == True)  # noqa: E712

        if with_latest_reading:
            from models.reading import Reading

            query = query.options(
                selectinload(
                    Device.readings.and_(
                        Reading.timestamp
                        == select(func.max(Reading.timestamp))
                        .where(Reading.device_id == Device.id)
                        .scalar_subquery()
                    )
                )
            )

        query = query.offset(skip).limit(limit)
        result = await db.execute(query)
        return list(result.scalars().all())

    async def get_with_latest_reading(
        self, db: AsyncSession, *, id: int
    ) -> Optional[Device]:
        """
        Get a device with its readings preloaded.

        Args:
            db: Database session
            id: Device ID

        Returns:
            Optional[Device]: Device with readings or None
        """
        query = (
            select(Device).options(selectinload(Device.readings)).where(Device.id == id)
        )
        result = await db.execute(query)
        return result.scalar_one_or_none()

    async def is_owner(self, db: AsyncSession, *, device_id: int, user_id: int) -> bool:
        """
        Check if a user is the owner of a device.

        Args:
            db: Database session
            device_id: Device ID
            user_id: User ID

        Returns:
            bool: True if user owns the device, False otherwise
        """
        device = await self.get(db, id=device_id)
        if not device:
            return False
        return device.owner_id == user_id

    async def get_active_devices(
        self, db: AsyncSession, *, skip: int = 0, limit: int = 100
    ) -> List[Device]:
        """
        Get all active devices.

        Args:
            db: Database session
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List[Device]: List of active devices
        """
        query = select(Device).where(Device.is_active == True).offset(skip).limit(limit)  # noqa: E712
        result = await db.execute(query)
        return list(result.scalars().all())

    async def deactivate(self, db: AsyncSession, *, id: int) -> Optional[Device]:
        """
        Deactivate a device.

        Args:
            db: Database session
            id: Device ID

        Returns:
            Optional[Device]: Updated device or None
        """
        device = await self.get(db, id=id)
        if not device:
            return None

        device.is_active = False
        await db.commit()
        await db.refresh(device)
        return device

    async def bulk_update_status(
        self, db: AsyncSession, *, device_ids: List[int], is_active: bool
    ) -> List[Device]:
        """
        Bulk update the active status of multiple devices.

        Args:
            db: Database session
            device_ids: List of device IDs to update
            is_active: New active status

        Returns:
            List[Device]: List of updated devices
        """
        query = select(Device).where(Device.id.in_(device_ids))
        result = await db.execute(query)
        devices = list(result.scalars().all())

        for device in devices:
            device.is_active = is_active

        await db.commit()
        for device in devices:
            await db.refresh(device)

        return devices

    async def get_inactive_devices(
        self, db: AsyncSession, *, min_inactive_days: int = 30
    ) -> List[Device]:
        """
        Get devices that haven't sent readings for a specified period.

        Args:
            db: Database session
            min_inactive_days: Minimum days of inactivity

        Returns:
            List[Device]: List of inactive devices
        """
        cutoff_date = datetime.utcnow() - timedelta(days=min_inactive_days)

        subquery = (
            select(Reading.device_id)
            .where(Reading.timestamp >= cutoff_date)
            .group_by(Reading.device_id)
            .scalar_subquery()
        )

        query = select(Device).where(
            and_(Device.is_active == True, Device.id.notin_(subquery))  # noqa: E712
        )

        result = await db.execute(query)
        return list(result.scalars().all())

    async def get_reading_statistics(
        self,
        db: AsyncSession,
        *,
        device_id: int,
        reading_type: ReadingType,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> Optional[dict]:
        """
        Get statistics for device readings with offsets applied.

        Args:
            db: Database session
            device_id: Device ID
            reading_type: Type of reading (temperature/humidity)
            start_time: Start time for statistics calculation
            end_time: End time for statistics calculation

        Returns:
            Optional[dict]: Dictionary containing min, max, and average values with offsets applied
        """
        # Get the device to access its offsets
        device = await self.get(db, id=device_id)
        if not device:
            return None

        # Build query with time filters
        query = (
            select(
                func.min(Reading.value).label("min_value"),
                func.max(Reading.value).label("max_value"),
                func.avg(Reading.value).label("avg_value"),
            )
            .where(
                and_(
                    Reading.device_id == device_id,
                    Reading.reading_type == reading_type,
                )
            )
        )

        if start_time:
            query = query.where(Reading.timestamp >= start_time)
        if end_time:
            query = query.where(Reading.timestamp <= end_time)

        result = await db.execute(query)
        stats = result.one()

        # Apply offset to statistics
        offset = (
            device.temperature_offset
            if reading_type == ReadingType.TEMPERATURE
            else device.humidity_offset
        )
        offset = offset or 0.0

        return type("Statistics", (), {
            "min_value": stats.min_value + offset if stats.min_value is not None else None,
            "max_value": stats.max_value + offset if stats.max_value is not None else None,
            "avg_value": stats.avg_value + offset if stats.avg_value is not None else None,
        })


# Create singleton instance for use across the application
device = CRUDDevice(Device)
