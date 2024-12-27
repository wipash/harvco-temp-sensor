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
            device_id="test-device-001", name="Test Device", is_active=True
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
            email="deviceowner@example.com", password="password123", is_active=True
        )
        user = await crud_user.create(db_session, obj_in=user_in)

        # Create device with owner
        device_in = DeviceCreate(
            device_id="test-device-002", name="Owner's Device", is_active=True
        )
        device = await crud_device.create_with_owner(
            db_session, obj_in=device_in, owner_id=user.id
        )

        assert device.owner_id == user.id
        assert device.device_id == device_in.device_id

    async def test_get_device_by_device_id(self, db_session: AsyncSession):
        """Test retrieving a device by its device_id."""
        device_in = DeviceCreate(device_id="test-device-003", name="Test Device")
        created_device = await crud_device.create(db_session, obj_in=device_in)

        fetched_device = await crud_device.get_by_device_id(
            db_session, device_id="test-device-003"
        )

        assert fetched_device is not None
        assert fetched_device.id == created_device.id

        # Test non-existent device_id
        non_existent = await crud_device.get_by_device_id(
            db_session, device_id="non-existent"
        )
        assert non_existent is None

    async def test_update_device(self, db_session: AsyncSession):
        """Test updating device attributes."""
        # Create initial device
        device_in = DeviceCreate(
            device_id="test-device-004", name="Original Name", is_active=True
        )
        device = await crud_device.create(db_session, obj_in=device_in)

        # Update device
        update_data = DeviceUpdate(name="Updated Name", is_active=False)
        updated_device = await crud_device.update(
            db_session, db_obj=device, obj_in=update_data
        )

        assert updated_device.name == "Updated Name"
        assert not updated_device.is_active
        assert updated_device.device_id == device.device_id  # Should remain unchanged

    async def test_deactivate_device(self, db_session: AsyncSession):
        """Test deactivating a device."""
        device_in = DeviceCreate(
            device_id="test-device-005", name="Active Device", is_active=True
        )
        device = await crud_device.create(db_session, obj_in=device_in)

        deactivated = await crud_device.deactivate(db_session, id=device.id)
        assert not deactivated.is_active

        # Verify deactivation persists
        fetched = await crud_device.get(db_session, id=device.id)
        assert not fetched.is_active

    async def test_get_inactive_devices(self, db_session: AsyncSession):
        """Test getting inactive devices based on reading timestamps."""
        # Create a device with old readings
        device_in = DeviceCreate(
            device_id="inactive-device", name="Inactive Device", is_active=True
        )
        device = await crud_device.create(db_session, obj_in=device_in)

        # Add an old reading
        old_reading = Reading(
            device_id=device.id,
            reading_type=ReadingType.TEMPERATURE,
            value=20.0,
            timestamp=datetime.utcnow() - timedelta(days=31),
        )
        db_session.add(old_reading)
        await db_session.commit()

        # Get inactive devices
        inactive_devices = await crud_device.get_inactive_devices(
            db_session, min_inactive_days=30
        )

        assert len(inactive_devices) == 1
        assert inactive_devices[0].id == device.id

    async def test_get_with_latest_reading(self, db_session: AsyncSession):
        """Test retrieving a device with its latest reading."""
        # Create device
        device_in = DeviceCreate(
            device_id="test-latest-reading", name="Test Device", is_active=True
        )
        device = await crud_device.create(db_session, obj_in=device_in)

        # Add multiple readings at different times
        old_reading = Reading(
            device_id=device.id,
            reading_type=ReadingType.TEMPERATURE,
            value=20.0,
            timestamp=datetime.utcnow() - timedelta(hours=1),
        )
        new_reading = Reading(
            device_id=device.id,
            reading_type=ReadingType.TEMPERATURE,
            value=22.0,
            timestamp=datetime.utcnow(),
        )
        db_session.add_all([old_reading, new_reading])
        await db_session.commit()

        # Get device with latest reading
        device_with_reading = await crud_device.get_with_latest_reading(
            db_session, id=device.id
        )

        assert device_with_reading is not None
        assert len(device_with_reading.readings) > 0
        latest_reading = max(device_with_reading.readings, key=lambda r: r.timestamp)
        assert latest_reading.value == 22.0

    async def test_bulk_update_status(self, db_session: AsyncSession):
        """Test bulk updating device status."""
        # Create multiple devices
        devices = []
        for i in range(3):
            device_in = DeviceCreate(
                device_id=f"bulk-test-{i}", name=f"Bulk Test Device {i}", is_active=True
            )
            device = await crud_device.create(db_session, obj_in=device_in)
            devices.append(device)

        # Bulk deactivate devices
        device_ids = [device.id for device in devices]
        updated_devices = await crud_device.bulk_update_status(
            db_session, device_ids=device_ids, is_active=False
        )

        assert len(updated_devices) == 3
        assert all(not device.is_active for device in updated_devices)

    async def test_device_duplicate_id(self, db_session: AsyncSession):
        """Test handling of duplicate device_id creation."""
        device_in = DeviceCreate(
            device_id="duplicate-test", name="Original Device", is_active=True
        )
        await crud_device.create(db_session, obj_in=device_in)

        # Attempt to create device with same device_id
        duplicate_device = DeviceCreate(
            device_id="duplicate-test", name="Duplicate Device", is_active=True
        )

        with pytest.raises(Exception):  # Should raise an integrity error
            await crud_device.create(db_session, obj_in=duplicate_device)

    async def test_device_ownership_transfer(self, db_session: AsyncSession):
        """Test transferring device ownership between users."""
        # Create two users
        user1_in = UserCreate(email="user1@example.com", password="password123")
        user2_in = UserCreate(email="user2@example.com", password="password123")
        user1 = await crud_user.create(db_session, obj_in=user1_in)
        user2 = await crud_user.create(db_session, obj_in=user2_in)

        # Create device owned by user1
        device_in = DeviceCreate(device_id="transfer-test", name="Transfer Test Device")
        device = await crud_device.create_with_owner(
            db_session, obj_in=device_in, owner_id=user1.id
        )

        # Transfer ownership to user2
        update_data = {"owner_id": user2.id}
        updated_device = await crud_device.update(
            db_session, db_obj=device, obj_in=update_data
        )

        assert updated_device.owner_id == user2.id
        assert await crud_device.is_owner(
            db_session, device_id=device.id, user_id=user2.id
        )
        assert not await crud_device.is_owner(
            db_session, device_id=device.id, user_id=user1.id
        )

    async def test_device_name_update(self, db_session: AsyncSession):
        """Test updating device name."""
        device_in = DeviceCreate(device_id="name-update-test", name="Original Name")
        device = await crud_device.create(db_session, obj_in=device_in)

        # Update with valid name
        update_data = DeviceUpdate(name="New Name")
        updated_device = await crud_device.update(
            db_session, db_obj=device, obj_in=update_data
        )
        assert updated_device.name == "New Name"

        # Update with None (should be allowed as per schema)
        update_data = DeviceUpdate(name=None)
        updated_device = await crud_device.update(
            db_session, db_obj=device, obj_in=update_data
        )
        assert updated_device.name is None

    async def test_get_multi_by_owner_with_filters(self, db_session: AsyncSession):
        """Test getting devices with various filters."""
        # Create owner
        user_in = UserCreate(email="devicefilter@example.com", password="password123")
        user = await crud_user.create(db_session, obj_in=user_in)

        # Create mix of active and inactive devices
        devices_data = [
            ("filter-device-1", True),
            ("filter-device-2", False),
            ("filter-device-3", True),
        ]

        for device_id, is_active in devices_data:
            device_in = DeviceCreate(
                device_id=device_id,
                name=f"Filter Test {device_id}",
                is_active=is_active,
            )
            await crud_device.create_with_owner(
                db_session, obj_in=device_in, owner_id=user.id
            )

        # Test active only filter
        active_devices = await crud_device.get_multi_by_owner_with_filters(
            db_session, owner_id=user.id, active_only=True
        )
        assert len(active_devices) == 2

        # Test pagination
        paginated_devices = await crud_device.get_multi_by_owner_with_filters(
            db_session, owner_id=user.id, skip=1, limit=1, active_only=False
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
            db_session, obj_in=device_in, owner_id=user1.id
        )

        # Verify ownership
        assert await crud_device.is_owner(
            db_session, device_id=device.id, user_id=user1.id
        )
        assert not await crud_device.is_owner(
            db_session, device_id=device.id, user_id=user2.id
        )

    async def test_device_offsets(self, db_session: AsyncSession):
        """Test device temperature and humidity offset functionality."""
        # Create a device with offsets
        device_in = DeviceCreate(
            device_id="offset-test-device",
            name="Offset Test Device",
            temperature_offset=1.5,
            humidity_offset=-2.0,
        )
        device = await crud_device.create(db_session, obj_in=device_in)

        assert device.temperature_offset == 1.5
        assert device.humidity_offset == -2.0

        # Test updating offsets
        update_data = DeviceUpdate(temperature_offset=2.0, humidity_offset=-1.0)
        updated_device = await crud_device.update(
            db_session, db_obj=device, obj_in=update_data
        )

        assert updated_device.temperature_offset == 2.0
        assert updated_device.humidity_offset == -1.0

        # Test partial offset updates
        partial_update = DeviceUpdate(temperature_offset=0.5)
        partially_updated = await crud_device.update(
            db_session, db_obj=updated_device, obj_in=partial_update
        )

        assert partially_updated.temperature_offset == 0.5
        assert partially_updated.humidity_offset == -1.0  # Should remain unchanged

    async def test_device_offset_validation(self, db_session: AsyncSession):
        """Test validation of device offset values."""
        # Test creating device with extreme offsets
        device_in = DeviceCreate(
            device_id="extreme-offset-device",
            name="Extreme Offset Device",
            temperature_offset=100.0,  # Unreasonable value
            humidity_offset=50.0,  # Unreasonable value
        )

        # This should raise a validation error
        with pytest.raises(ValueError):
            await crud_device.create(db_session, obj_in=device_in)

        # Test with null offsets (should be allowed)
        null_offset_device = DeviceCreate(
            device_id="null-offset-device",
            name="Null Offset Device",
            temperature_offset=None,
            humidity_offset=None,
        )
        device = await crud_device.create(db_session, obj_in=null_offset_device)

        assert device.temperature_offset is None
        assert device.humidity_offset is None

    async def test_offset_application_to_readings(self, db_session: AsyncSession):
        """Test how offsets are applied to readings."""
        # Create device with known offsets
        device_in = DeviceCreate(
            device_id="reading-offset-device",
            name="Reading Offset Device",
            temperature_offset=1.0,
            humidity_offset=2.0,
        )
        device = await crud_device.create(db_session, obj_in=device_in)

        # Create readings
        readings = [
            Reading(
                device_id=device.id,
                reading_type=ReadingType.TEMPERATURE,
                value=20.0,
                timestamp=datetime.utcnow(),
            ),
            Reading(
                device_id=device.id,
                reading_type=ReadingType.HUMIDITY,
                value=50.0,
                timestamp=datetime.utcnow(),
            ),
        ]

        db_session.add_all(readings)
        await db_session.commit()

        # Get readings with offsets applied
        device_with_readings = await crud_device.get_with_latest_reading(
            db_session, id=device.id
        )

        # Test temperature reading with offset
        temp_reading = next(
            r
            for r in device_with_readings.readings
            if r.reading_type == ReadingType.TEMPERATURE
        )
        assert temp_reading.get_adjusted_value() == 21.0  # 20.0 + 1.0

        # Test humidity reading with offset
        humidity_reading = next(
            r
            for r in device_with_readings.readings
            if r.reading_type == ReadingType.HUMIDITY
        )
        assert humidity_reading.get_adjusted_value() == 52.0  # 50.0 + 2.0

    async def test_offset_statistics(self, db_session: AsyncSession):
        """Test offset application in statistical calculations."""
        # Create device with offsets
        device_in = DeviceCreate(
            device_id="stats-offset-device",
            name="Stats Offset Device",
            temperature_offset=1.0,
            humidity_offset=-1.0,
        )
        device = await crud_device.create(db_session, obj_in=device_in)

        # Create multiple readings over time
        readings = [
            Reading(
                device_id=device.id,
                reading_type=ReadingType.TEMPERATURE,
                value=value,
                timestamp=datetime.utcnow() - timedelta(hours=i),
            )
            for i, value in enumerate([20.0, 22.0, 21.0])
        ]

        db_session.add_all(readings)
        await db_session.commit()

        # Get statistics with offsets applied
        start_time = datetime.utcnow() - timedelta(days=1)
        end_time = datetime.utcnow()

        stats = await crud_device.get_reading_statistics(
            db_session,
            device_id=device.id,
            reading_type=ReadingType.TEMPERATURE,
            start_time=start_time,
            end_time=end_time,
        )

        # Verify statistics with offset
        assert stats.min_value == 21.0  # 20.0 + 1.0
        assert stats.max_value == 23.0  # 22.0 + 1.0
        assert stats.avg_value == 22.0  # 21.0 + 1.0

    async def test_offset_edge_cases(self, db_session: AsyncSession):
        """Test edge cases for offset handling."""
        # Test with zero offsets
        device_in = DeviceCreate(
            device_id="zero-offset-device",
            name="Zero Offset Device",
            temperature_offset=0.0,
            humidity_offset=0.0,
        )
        device = await crud_device.create(db_session, obj_in=device_in)

        # Create reading
        reading = Reading(
            device_id=device.id,
            reading_type=ReadingType.TEMPERATURE,
            value=20.0,
            timestamp=datetime.utcnow(),
        )
        db_session.add(reading)
        await db_session.commit()

        # Verify zero offset doesn't affect value
        device_with_reading = await crud_device.get_with_latest_reading(
            db_session, id=device.id
        )
        assert device_with_reading.readings[0].get_adjusted_value() == 20.0

        # Test with very small offsets
        update_data = DeviceUpdate(temperature_offset=0.0001, humidity_offset=-0.0001)
        updated_device = await crud_device.update(
            db_session, db_obj=device, obj_in=update_data
        )

        assert abs(updated_device.temperature_offset - 0.0001) < 1e-6
        assert abs(updated_device.humidity_offset - (-0.0001)) < 1e-6
