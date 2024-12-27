import pytest
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.crud_reading import reading as crud_reading
from app.crud.crud_device import device as crud_device
from app.schemas.reading import ReadingCreate
from app.schemas.device import DeviceCreate
from app.models.reading import ReadingType

pytestmark = pytest.mark.asyncio

class TestReadingCRUD:
    async def test_create_reading(self, db_session: AsyncSession):
        """Test creating a new reading."""
        # First create a device
        device_in = DeviceCreate(
            device_id="test-device-readings",
            name="Test Device",
            is_active=True
        )
        device = await crud_device.create(db_session, obj_in=device_in)
        
        # Create reading
        reading_in = ReadingCreate(
            reading_type=ReadingType.TEMPERATURE,
            value=23.5,
            device_id=device.device_id,
            timestamp=datetime.utcnow()
        )
        
        reading = await crud_reading.create_with_device(
            db_session,
            obj_in=reading_in,
            device_id=device.id
        )
        
        assert reading.value == reading_in.value
        assert reading.reading_type == reading_in.reading_type
        assert reading.device_id == device.id

    async def test_get_reading(self, db_session: AsyncSession):
        """Test retrieving a reading by ID."""
        # Create device and reading
        device_in = DeviceCreate(device_id="test-get-reading", name="Test Device")
        device = await crud_device.create(db_session, obj_in=device_in)
        
        reading_in = ReadingCreate(
            reading_type=ReadingType.TEMPERATURE,
            value=25.0,
            device_id=device.device_id
        )
        created_reading = await crud_reading.create_with_device(
            db_session,
            obj_in=reading_in,
            device_id=device.id
        )
        
        # Retrieve the reading
        fetched_reading = await crud_reading.get(db_session, id=created_reading.id)
        
        assert fetched_reading is not None
        assert fetched_reading.id == created_reading.id
        assert fetched_reading.value == reading_in.value

    async def test_get_latest_by_device(self, db_session: AsyncSession):
        """Test getting the latest reading for a device."""
        # Create device
        device_in = DeviceCreate(device_id="test-latest", name="Test Device")
        device = await crud_device.create(db_session, obj_in=device_in)
        
        # Create multiple readings at different times
        timestamps = [
            datetime.utcnow() - timedelta(hours=2),
            datetime.utcnow() - timedelta(hours=1),
            datetime.utcnow()
        ]
        values = [20.0, 22.0, 24.0]
        
        for timestamp, value in zip(timestamps, values):
            reading_in = ReadingCreate(
                reading_type=ReadingType.TEMPERATURE,
                value=value,
                device_id=device.device_id,
                timestamp=timestamp
            )
            await crud_reading.create_with_device(
                db_session,
                obj_in=reading_in,
                device_id=device.id
            )
        
        # Get latest reading
        latest_reading = await crud_reading.get_latest_by_device(
            db_session,
            device_id=device.id
        )
        
        assert latest_reading is not None
        assert latest_reading.value == 24.0

    async def test_get_readings_by_type(self, db_session: AsyncSession):
        """Test retrieving readings by type."""
        # Create device
        device_in = DeviceCreate(device_id="test-type", name="Test Device")
        device = await crud_device.create(db_session, obj_in=device_in)
        
        # Create both temperature and humidity readings
        readings_data = [
            (ReadingType.TEMPERATURE, 25.0),
            (ReadingType.HUMIDITY, 60.0),
            (ReadingType.TEMPERATURE, 26.0)
        ]
        
        for reading_type, value in readings_data:
            reading_in = ReadingCreate(
                reading_type=reading_type,
                value=value,
                device_id=device.device_id
            )
            await crud_reading.create_with_device(
                db_session,
                obj_in=reading_in,
                device_id=device.id
            )
        
        # Get temperature readings
        temp_readings = await crud_reading.get_readings_by_type(
            db_session,
            reading_type=ReadingType.TEMPERATURE
        )
        
        assert len(temp_readings) == 2
        assert all(r.reading_type == ReadingType.TEMPERATURE for r in temp_readings)

    async def test_invalid_reading_values(self, db_session: AsyncSession):
        """Test handling of invalid reading values."""
        device_in = DeviceCreate(device_id="test-invalid", name="Test Device")
        device = await crud_device.create(db_session, obj_in=device_in)
        
        # Test with various invalid values
        invalid_values = [float('inf'), float('-inf')]  # Remove NaN for SQLite compatibility
        
        for value in invalid_values:
            reading_in = ReadingCreate(
                reading_type=ReadingType.TEMPERATURE,
                value=value,
                device_id=device.device_id
            )
            
            # Should still create the reading but handle invalid values appropriately
            reading = await crud_reading.create_with_device(
                db_session,
                obj_in=reading_in,
                device_id=device.id
            )
            
            # Verify the reading was created
            assert reading is not None
            
            # When retrieving statistics or filtered readings,
            # these invalid values should be handled appropriately
            stats = await crud_reading.get_statistics(
                db_session,
                device_id=device.id,
                reading_type=ReadingType.TEMPERATURE
            )
            
            # Stats should not include invalid values
            assert isinstance(stats["avg"], float)
            assert stats["avg"] != float('inf')
            assert stats["avg"] != float('-inf')
            assert stats["avg"] == stats["avg"]  # NaN check

        # Add separate test for NaN handling
        try:
            reading_in = ReadingCreate(
                reading_type=ReadingType.TEMPERATURE,
                value=float('nan'),
                device_id=device.device_id
            )
            await crud_reading.create_with_device(
                db_session,
                obj_in=reading_in,
                device_id=device.id
            )
            pytest.fail("Expected NaN value to raise an error")
        except Exception as e:
            assert "IntegrityError" in str(e.__class__.__name__)
