import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timedelta

from app.crud.crud_device import device as crud_device
from app.crud.crud_user import user as crud_user
from app.schemas.device import DeviceCreate, DeviceUpdate
from app.schemas.user import UserCreate
from app.models.reading import Reading, ReadingType

pytestmark = pytest.mark.asyncio

class TestDeviceCRUD:
    async def test_create_device(self, db_session: AsyncSession):
        """Test creating a device without owner."""
        device_in = DeviceCreate(
            device_id="test-device-001",
            name="Test Device",
            is_active=True
        )
        device = await crud_device.create(db_session, obj_in=device_in)
        
        assert device.device_id == device_in.device_id
        assert device.name == device_in.name
        assert device.is_active == device_in.is_active
        assert device.owner_id is None

    async def test_create_device_with_owner(self, db_session: AsyncSession):
        """Test creating a device with an owner."""
        # Create a user first
        user_in = UserCreate(
            email="deviceowner@example.com",
            password="password123",
            is_active=True
        )
        user = await crud_user.create(db_session, obj_in=user_in)
        
        # Create device with owner
        device_in = DeviceCreate(
            device_id="test-device-002",
            name="Owner's Device",
            is_active=True
        )
        device = await crud_device.create_with_owner(
            db_session,
            obj_in=device_in,
            owner_id=user.id
        )
        
        assert device.owner_id == user.id
        assert device.device_id == device_in.device_id

    async def test_get_device_by_device_id(self, db_session: AsyncSession):
        """Test retrieving a device by its device_id."""
        device_in = DeviceCreate(
            device_id="test-device-003",
            name="Test Device"
        )
        created_device = await crud_device.create(db_session, obj_in=device_in)
        
        fetched_device = await crud_device.get_by_device_id(
            db_session,
            device_id="test-device-003"
        )
        
        assert fetched_device is not None
        assert fetched_device.id == created_device.id
        
        # Test non-existent device_id
        non_existent = await crud_device.get_by_device_id(
            db_session,
            device_id="non-existent"
        )
        assert non_existent is None

    async def test_update_device(self, db_session: AsyncSession):
        """Test updating device attributes."""
        # Create initial device
        device_in = DeviceCreate(
            device_id="test-device-004",
            name="Original Name",
            is_active=True
        )
        device = await crud_device.create(db_session, obj_in=device_in)
        
        # Update device
        update_data = DeviceUpdate(
            name="Updated Name",
            is_active=False
        )
        updated_device = await crud_device.update(
            db_session,
            db_obj=device,
            obj_in=update_data
        )
        
        assert updated_device.name == "Updated Name"
        assert not updated_device.is_active
        assert updated_device.device_id == device.device_id  # Should remain unchanged

    async def test_deactivate_device(self, db_session: AsyncSession):
        """Test deactivating a device."""
        device_in = DeviceCreate(
            device_id="test-device-005",
            name="Active Device",
            is_active=True
        )
        device = await crud_device.create(db_session, obj_in=device_in)
        
        deactivated = await crud_device.deactivate(db_session, id=device.id)
        assert not deactivated.is_active
        
        # Verify deactivation persists
        fetched = await crud_device.get(db_session, id=device.id)
        assert not fetched.is_active

    async def test_bulk_update_status(self, db_session: AsyncSession):
        """Test bulk updating device statuses."""
        # Create multiple devices
        devices = []
        for i in range(3):
            device_in = DeviceCreate(
                device_id=f"bulk-device-{i}",
                name=f"Bulk Device {i}",
                is_active=True
            )
            device = await crud_device.create(db_session, obj_in=device_in)
            devices.append(device)
        
        # Bulk deactivate
        device_ids = [d.id for d in devices]
        updated_devices = await crud_device.bulk_update_status(
            db_session,
            device_ids=device_ids,
            is_active=False
        )
        
        assert len(updated_devices) == 3
        assert all(not d.is_active for d in updated_devices)

    async def test_get_inactive_devices(self, db_session: AsyncSession):
        """Test getting inactive devices based on reading timestamps."""
        # Create a device with old readings
        device_in = DeviceCreate(
            device_id="inactive-device",
            name="Inactive Device",
            is_active=True
        )
        device = await crud_device.create(db_session, obj_in=device_in)
        
        # Add an old reading
        old_reading = Reading(
            device_id=device.id,
            reading_type=ReadingType.TEMPERATURE,
            value=20.0,
            timestamp=datetime.utcnow() - timedelta(days=31)
        )
        db_session.add(old_reading)
        await db_session.commit()
        
        # Get inactive devices
        inactive_devices = await crud_device.get_inactive_devices(
            db_session,
            min_inactive_days=30
        )
        
        assert len(inactive_devices) == 1
        assert inactive_devices[0].id == device.id

    async def test_get_multi_by_owner_with_filters(self, db_session: AsyncSession):
        """Test getting devices with various filters."""
        # Create owner
        user_in = UserCreate(
            email="devicefilter@example.com",
            password="password123"
        )
        user = await crud_user.create(db_session, obj_in=user_in)
        
        # Create mix of active and inactive devices
        devices_data = [
            ("filter-device-1", True),
            ("filter-device-2", False),
            ("filter-device-3", True)
        ]
        
        for device_id, is_active in devices_data:
            device_in = DeviceCreate(
                device_id=device_id,
                name=f"Filter Test {device_id}",
                is_active=is_active
            )
            await crud_device.create_with_owner(
                db_session,
                obj_in=device_in,
                owner_id=user.id
            )
        
        # Test active only filter
        active_devices = await crud_device.get_multi_by_owner_with_filters(
            db_session,
            owner_id=user.id,
            active_only=True
        )
        assert len(active_devices) == 2
        
        # Test pagination
        paginated_devices = await crud_device.get_multi_by_owner_with_filters(
            db_session,
            owner_id=user.id,
            skip=1,
            limit=1,
            active_only=False
        )
        assert len(paginated_devices) == 1

    async def test_is_owner(self, db_session: AsyncSession):
        """Test ownership verification."""
        # Create two users
        user1_in = UserCreate(email="owner1@example.com", password="password123")
        user2_in = UserCreate(email="owner2@example.com", password="password123")
        user1 = await crud_user.create(db_session, obj_in=user1_in)
        user2 = await crud_user.create(db_session, obj_in=user2_in)
        
        # Create device owned by user1
        device_in = DeviceCreate(device_id="owned-device", name="Owned Device")
        device = await crud_device.create_with_owner(
            db_session,
            obj_in=device_in,
            owner_id=user1.id
        )
        
        # Verify ownership
        assert await crud_device.is_owner(db_session, device_id=device.id, user_id=user1.id)
        assert not await crud_device.is_owner(db_session, device_id=device.id, user_id=user2.id)
