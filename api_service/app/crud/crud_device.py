"""
CRUD operations for Device model.

This module implements Create, Read, Update, Delete operations for devices using
the repository pattern.
"""

from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.device import Device
from app.models.reading import Reading, ReadingType
from app.schemas.device import DeviceCreate, DeviceUpdate
from app.crud.base import CRUDBase

class CRUDDevice(CRUDBase[Device, DeviceCreate, DeviceUpdate]):
    """
    CRUD operations for Device model.
    Inherits basic CRUD operations from CRUDBase.
    """

    async def create_with_owner(
        self,
        db: AsyncSession,
        *,
        obj_in: DeviceCreate,
        owner_id: int
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
        db_obj = Device(
            **obj_in.model_dump(exclude={'id'}),
            owner_id=owner_id
        )
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj

    async def get_by_device_id(
        self,
        db: AsyncSession,
        *,
        device_id: str
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
        with_latest_reading: bool = False
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
            query = query.where(Device.is_active == True)
            
        if with_latest_reading:
            from app.models.reading import Reading
            query = query.options(
                selectinload(
                    Device.readings.and_(
                        Reading.timestamp == select(func.max(Reading.timestamp))
                        .where(Reading.device_id == Device.id)
                        .scalar_subquery()
                    )
                )
            )
            
        query = query.offset(skip).limit(limit)
        result = await db.execute(query)
        return list(result.scalars().all())

    async def get_with_latest_reading(
        self,
        db: AsyncSession,
        *,
        id: int
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
            select(Device)
            .options(selectinload(Device.readings))
            .where(Device.id == id)
        )
        result = await db.execute(query)
        return result.scalar_one_or_none()

    async def is_owner(
        self,
        db: AsyncSession,
        *,
        device_id: int,
        user_id: int
    ) -> bool:
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
        self,
        db: AsyncSession,
        *,
        skip: int = 0,
        limit: int = 100
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
        query = (
            select(Device)
            .where(Device.is_active == True)
            .offset(skip)
            .limit(limit)
        )
        result = await db.execute(query)
        return list(result.scalars().all())

    async def deactivate(
        self,
        db: AsyncSession,
        *,
        id: int
    ) -> Optional[Device]:
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

    async def get_device_stats(
        self,
        db: AsyncSession,
        *,
        device_id: int,
        reading_type: Optional[ReadingType] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Get statistics for a device's readings.

        Args:
            db: Database session
            device_id: Device ID
            reading_type: Optional type of reading to filter
            start_date: Optional start date for filtering
            end_date: Optional end date for filtering

        Returns:
            Dict[str, Any]: Device statistics including reading counts and latest values
        """
        from sqlalchemy import and_, func, text, case
        import logging
        logger = logging.getLogger(__name__)
        
        # Base query filtering out NULL values only first
        base_conditions = [
            Reading.device_id == device_id,
            Reading.value.isnot(None)  # Filter out NULL values
        ]

        if reading_type:
            base_conditions.append(Reading.reading_type == reading_type)
        if start_date:
            base_conditions.append(Reading.timestamp >= start_date)
        if end_date:
            base_conditions.append(Reading.timestamp <= end_date)

        # Query for statistics
        query = select(
            func.count(Reading.id).label("total_readings"),
            func.min(case(
                (Reading.value == Reading.value, Reading.value),
                else_=None
            )).label("min_value"),
            func.max(case(
                (Reading.value == Reading.value, Reading.value),
                else_=None
            )).label("max_value"),
            func.avg(case(
                (Reading.value == Reading.value, Reading.value),
                else_=None
            )).label("avg_value")
        ).where(and_(*base_conditions))

        logger.debug(f"Statistics query: {query}")
        
        result = await db.execute(query)
        stats = result.one()
        
        logger.debug(f"Raw database stats: {stats}")

        # Get latest valid reading
        latest_query = (
            select(Reading)
            .where(
                and_(
                    *base_conditions,
                    Reading.value == Reading.value  # Add NaN filter for latest reading
                )
            )
            .order_by(Reading.timestamp.desc())
            .limit(1)
        )
        
        latest_result = await db.execute(latest_query)
        latest_reading = latest_result.scalar_one_or_none()

        # Helper function to safely convert values with default
        def safe_float(value, default: float = 0.0) -> float:
            if value is None:
                return default
            try:
                float_val = float(value)
                if float_val != float_val:  # NaN check
                    return default
                return float_val
            except (ValueError, TypeError):
                return default

        # Process statistics, using 0.0 as default for empty sets
        total_readings = int(stats.total_readings or 0)
        min_val = safe_float(stats.min_value, 0.0 if total_readings == 0 else None)
        max_val = safe_float(stats.max_value, 0.0 if total_readings == 0 else None)
        avg_val = safe_float(stats.avg_value, 0.0 if total_readings == 0 else None)

        result = {
            "total_readings": total_readings,
            "min_value": min_val,
            "max_value": max_val,
            "avg_value": avg_val,
            "latest_reading": {
                "value": latest_reading.value if latest_reading else None,
                "timestamp": latest_reading.timestamp if latest_reading else None
            } if latest_reading else None
        }
        
        logger.debug(f"Final processed stats: {result}")
        return result

    async def get_multi_by_owner_with_stats(
        self,
        db: AsyncSession,
        *,
        owner_id: int,
        skip: int = 0,
        limit: int = 100,
        include_inactive: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Get multiple devices with their statistics.

        Args:
            db: Database session
            owner_id: Owner ID
            skip: Number of records to skip
            limit: Maximum number of records to return
            include_inactive: Whether to include inactive devices

        Returns:
            List[Dict[str, Any]]: List of devices with their statistics
        """
        # Get devices
        query = select(Device).where(Device.owner_id == owner_id)
        if not include_inactive:
            query = query.where(Device.is_active == True)
        query = query.offset(skip).limit(limit)
        
        result = await db.execute(query)
        devices = list(result.scalars().all())

        # Get stats for each device
        devices_with_stats = []
        for device in devices:
            stats = await self.get_device_stats(db, device_id=device.id)
            devices_with_stats.append({
                "id": device.id,
                "device_id": device.device_id,
                "name": device.name,
                "is_active": device.is_active,
                "stats": stats
            })

        return devices_with_stats

    async def bulk_update_status(
        self,
        db: AsyncSession,
        *,
        device_ids: List[int],
        is_active: bool
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
        query = (
            select(Device)
            .where(Device.id.in_(device_ids))
        )
        result = await db.execute(query)
        devices = list(result.scalars().all())

        for device in devices:
            device.is_active = is_active

        await db.commit()
        for device in devices:
            await db.refresh(device)

        return devices

    async def get_inactive_devices(
        self,
        db: AsyncSession,
        *,
        min_inactive_days: int = 30
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

        query = (
            select(Device)
            .where(
                and_(
                    Device.is_active == True,
                    Device.id.notin_(subquery)
                )
            )
        )

        result = await db.execute(query)
        return list(result.scalars().all())

# Create singleton instance for use across the application
device = CRUDDevice(Device)
