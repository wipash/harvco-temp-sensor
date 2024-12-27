import pytest
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.reading import Reading, ReadingType
from app.models.device import Device
from app.schemas.device import DeviceCreate
from app.crud.crud_device import device as crud_device
from app.crud.crud_reading import reading as crud_reading

pytestmark = pytest.mark.asyncio

async def create_test_device_with_offsets(
    db: AsyncSession,
    device_id: str,
    temp_offset: float,
    humid_offset: float,
    owner_id: int
) -> Device:
    """Helper to create a test device with specified offsets."""
    device_in = DeviceCreate(
        device_id=device_id,
        name="Test Device",
        temperature_offset=temp_offset,
        humidity_offset=humid_offset
    )
    return await crud_device.create_with_owner(db, obj_in=device_in, owner_id=owner_id)

async def create_test_reading(
    db: AsyncSession,
    device_id: int,
    reading_type: ReadingType,
    value: float,
    timestamp: datetime = None
) -> Reading:
    """Helper to create a test reading."""
    if timestamp is None:
        timestamp = datetime.utcnow()
    
    reading = Reading(
        device_id=device_id,
        reading_type=reading_type,
        value=value,
        timestamp=timestamp
    )
    db.add(reading)
    await db.commit()
    await db.refresh(reading)
    return reading

class TestReadingOffsets:
    async def test_single_reading_temperature_offset(self, db_session: AsyncSession, test_user):
        """Test temperature offset application for a single reading."""
        # Create device with temperature offset
        device = await create_test_device_with_offsets(
            db_session, "test-device-1", 
            temp_offset=2.5, 
            humid_offset=0.0,
            owner_id=test_user.id
        )
        
        # Create temperature reading
        reading = await create_test_reading(
            db_session,
            device.id,
            ReadingType.TEMPERATURE,
            value=20.0
        )
        
        # Get reading with offset applied
        result = await crud_reading.get_latest_by_device(
            db_session,
            device_id=device.id,
            reading_type=ReadingType.TEMPERATURE
        )
        
        assert result.value == 22.5  # 20.0 + 2.5

    async def test_single_reading_humidity_offset(self, db_session: AsyncSession, test_user):
        """Test humidity offset application for a single reading."""
        device = await create_test_device_with_offsets(
            db_session, "test-device-2",
            temp_offset=0.0,
            humid_offset=5.0,
            owner_id=test_user.id
        )
        
        reading = await create_test_reading(
            db_session,
            device.id,
            ReadingType.HUMIDITY,
            value=50.0
        )
        
        result = await crud_reading.get_latest_by_device(
            db_session,
            device_id=device.id,
            reading_type=ReadingType.HUMIDITY
        )
        
        assert result.value == 55.0  # 50.0 + 5.0

    async def test_multiple_readings_with_offsets(self, db_session: AsyncSession, test_user):
        """Test offset application for multiple readings."""
        device = await create_test_device_with_offsets(
            db_session, "test-device-3",
            temp_offset=1.0,
            humid_offset=2.0,
            owner_id=test_user.id
        )
        
        # Create multiple readings
        base_time = datetime.utcnow()
        readings = [
            await create_test_reading(
                db_session, device.id,
                ReadingType.TEMPERATURE if i % 2 == 0 else ReadingType.HUMIDITY,
                value=float(i),
                timestamp=base_time + timedelta(minutes=i)
            )
            for i in range(5)
        ]
        
        # Get readings with offsets
        results = await crud_reading.get_by_device(
            db_session,
            device_id=device.id,
            start_date=base_time,
            end_date=base_time + timedelta(hours=1)
        )
        
        for result in results:
            if result.reading_type == ReadingType.TEMPERATURE:
                assert result.value == float(result.id - 1) + 1.0  # Add temp offset
            else:
                assert result.value == float(result.id - 1) + 2.0  # Add humid offset

    async def test_null_offsets(self, db_session: AsyncSession, test_user):
        """Test handling of null offsets."""
        # Create device with null offsets
        device_in = DeviceCreate(
            device_id="test-device-4",
            name="Test Device",
            temperature_offset=None,
            humidity_offset=None
        )
        device = await crud_device.create_with_owner(
            db_session,
            obj_in=device_in,
            owner_id=test_user.id
        )
        
        # Create readings
        temp_reading = await create_test_reading(
            db_session, device.id,
            ReadingType.TEMPERATURE,
            value=25.0
        )
        
        humid_reading = await create_test_reading(
            db_session, device.id,
            ReadingType.HUMIDITY,
            value=60.0
        )
        
        # Verify no offset applied
        temp_result = await crud_reading.get_latest_by_device(
            db_session,
            device_id=device.id,
            reading_type=ReadingType.TEMPERATURE
        )
        assert temp_result.value == 25.0
        
        humid_result = await crud_reading.get_latest_by_device(
            db_session,
            device_id=device.id,
            reading_type=ReadingType.HUMIDITY
        )
        assert humid_result.value == 60.0

    async def test_statistics_with_offsets(self, db_session: AsyncSession, test_user):
        """Test statistics calculation with offsets applied."""
        device = await create_test_device_with_offsets(
            db_session, "test-device-5",
            temp_offset=1.5,
            humid_offset=0.0,
            owner_id=test_user.id
        )
        
        # Create temperature readings: 20.0, 22.0, 24.0
        base_time = datetime.utcnow()
        for i, value in enumerate([20.0, 22.0, 24.0]):
            await create_test_reading(
                db_session,
                device.id,
                ReadingType.TEMPERATURE,
                value=value,
                timestamp=base_time + timedelta(minutes=i)
            )
        
        stats = await crud_reading.get_statistics(
            db_session,
            device_id=device.id,
            reading_type=ReadingType.TEMPERATURE,
            start_date=base_time,
            end_date=base_time + timedelta(hours=1)
        )
        
        # Check statistics with offset
        assert stats["min"] == 21.5  # 20.0 + 1.5
        assert stats["max"] == 25.5  # 24.0 + 1.5
        assert stats["avg"] == 23.5  # 22.0 + 1.5

    async def test_edge_cases(self, db_session: AsyncSession, test_user):
        """Test edge cases for offset handling."""
        device = await create_test_device_with_offsets(
            db_session, "test-device-6",
            temp_offset=-1.0,  # Negative offset
            humid_offset=999.9,  # Large offset
            owner_id=test_user.id
        )
        
        # Test with zero value
        zero_reading = await create_test_reading(
            db_session,
            device.id,
            ReadingType.TEMPERATURE,
            value=0.0
        )
        
        result = await crud_reading.get_latest_by_device(
            db_session,
            device_id=device.id,
            reading_type=ReadingType.TEMPERATURE
        )
        assert result.value == -1.0  # 0.0 + (-1.0)
        
        # Test with very large value
        large_reading = await create_test_reading(
            db_session,
            device.id,
            ReadingType.HUMIDITY,
            value=99.9
        )
        
        result = await crud_reading.get_latest_by_device(
            db_session,
            device_id=device.id,
            reading_type=ReadingType.HUMIDITY
        )
        assert result.value == 1099.8  # 99.9 + 999.9

    async def test_missing_device(self, db_session: AsyncSession):
        """Test handling of readings for non-existent device."""
        reading = Reading(
            device_id=999999,  # Non-existent device ID
            reading_type=ReadingType.TEMPERATURE,
            value=20.0,
            timestamp=datetime.utcnow()
        )
        db_session.add(reading)
        await db_session.commit()
        
        result = await crud_reading.get_latest_by_device(
            db_session,
            device_id=999999,
            reading_type=ReadingType.TEMPERATURE
        )
        
        # Should return raw value without offset since device doesn't exist
        assert result.value == 20.0
