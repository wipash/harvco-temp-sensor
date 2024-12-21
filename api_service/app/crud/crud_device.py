"""
CRUD operations for Device model.

This module implements Create, Read, Update, Delete operations for devices using
the repository pattern.
"""

from typing import Optional, List
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.device import Device
from app.models.user import User
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

    async def get_by_serial_number(
        self,
        db: AsyncSession,
        *,
        serial_number: str
    ) -> Optional[Device]:
        """
        Get a device by its serial number.

        Args:
            db: Database session
            serial_number: Device serial number

        Returns:
            Optional[Device]: Found device or None
        """
        query = select(Device).where(Device.serial_number == serial_number)
        result = await db.execute(query)
        return result.scalar_one_or_none()

    async def get_multi_by_owner(
        self,
        db: AsyncSession,
        *,
        owner_id: int,
        skip: int = 0,
        limit: int = 100
    ) -> List[Device]:
        """
        Get multiple devices belonging to an owner.

        Args:
            db: Database session
            owner_id: ID of the owner
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List[Device]: List of devices
        """
        query = (
            select(Device)
            .where(Device.owner_id == owner_id)
            .offset(skip)
            .limit(limit)
        )
        result = await db.execute(query)
        return list(result.scalars().all())

    async def get_with_readings(
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

# Create singleton instance for use across the application
device = CRUDDevice(Device)
