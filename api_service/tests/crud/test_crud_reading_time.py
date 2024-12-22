import pytest
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.crud_reading import reading as crud_reading
from app.crud.crud_device import device as crud_device
from app.schemas.reading import ReadingCreate
from app.schemas.device import DeviceCreate
from app.models.reading import ReadingType

pytestmark = pytest.mark.asyncio

class TestReadingTimeAndAveraging:
    async def test_basic_time_filtering(self, db_session: AsyncSession):
        """Test basic time-based filtering of readings."""
        # Create a device
        device_in = DeviceCreate(device_id="test-time-filter", name="Test Device")
        device = await crud_device.create(db_session, obj_in=device_in)
        
        # Create readings at different times
        base_time = datetime(2024, 1, 1, 12, 0)  # Noon on Jan 1, 2024
        readings_data = [
            (20.0, base_time - timedelta(hours=2)),  # 10 AM
            (22.0, base_time - timedelta(hours=1)),  # 11 AM
            (24.0, base_time),                       # 12 PM
            (26.0, base_time + timedelta(hours=1)),  # 1 PM
        ]
        
        for value, timestamp in readings_data:
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
        
        # Test filtering with different time windows
        readings = await crud_reading.get_by_device(
            db_session,
            device_id=device.id,
            start_date=base_time - timedelta(hours=1.5),  # 10:30 AM
            end_date=base_time + timedelta(minutes=30),   # 12:30 PM
        )
        
        assert len(readings) == 2  # Should include 11 AM and 12 PM readings
        assert all(base_time - timedelta(hours=1.5) <= r.timestamp <= base_time + timedelta(minutes=30) 
                  for r in readings)

    async def test_averaging_threshold(self, db_session: AsyncSession):
        """Test averaging behavior when number of readings exceeds threshold."""
        device_in = DeviceCreate(device_id="test-averaging", name="Test Device")
        device = await crud_device.create(db_session, obj_in=device_in)
        
        # Create many readings over a short time period
        base_time = datetime(2024, 1, 1, 12, 0)
        num_readings = 600  # More than the default threshold
        
        for i in range(num_readings):
            reading_in = ReadingCreate(
                reading_type=ReadingType.TEMPERATURE,
                value=20.0 + (i * 0.1),  # Gradually increasing values
                device_id=device.device_id,
                timestamp=base_time + timedelta(minutes=i)
            )
            await crud_reading.create_with_device(
                db_session,
                obj_in=reading_in,
                device_id=device.id
            )
        
        # Retrieve with averaging (threshold=500)
        readings = await crud_reading.get_by_device(
            db_session,
            device_id=device.id,
            start_date=base_time,
            end_date=base_time + timedelta(minutes=num_readings),
            threshold=500
        )
        
        assert len(readings) <= 500
        # Verify averaging maintains value progression
        values = [r.value for r in readings]
        assert values[-1] > values[0]  # Last average should be higher than first

    async def test_multiple_reading_types_averaging(self, db_session: AsyncSession):
        """Test averaging behavior with multiple reading types."""
        device_in = DeviceCreate(device_id="test-multi-type", name="Test Device")
        device = await crud_device.create(db_session, obj_in=device_in)
        
        base_time = datetime(2024, 1, 1, 12, 0)
        readings_per_type = 100
        
        # Create interleaved temperature and humidity readings
        for i in range(readings_per_type):
            # Temperature reading
            temp_reading = ReadingCreate(
                reading_type=ReadingType.TEMPERATURE,
                value=20.0 + (i * 0.1),
                device_id=device.device_id,
                timestamp=base_time + timedelta(minutes=i*2)
            )
            await crud_reading.create_with_device(
                db_session,
                obj_in=temp_reading,
                device_id=device.id
            )
            
            # Humidity reading
            humid_reading = ReadingCreate(
                reading_type=ReadingType.HUMIDITY,
                value=50.0 + (i * 0.1),
                device_id=device.device_id,
                timestamp=base_time + timedelta(minutes=i*2+1)
            )
            await crud_reading.create_with_device(
                db_session,
                obj_in=humid_reading,
                device_id=device.id
            )
        
        # Retrieve and verify each type separately
        temp_readings = await crud_reading.get_by_device(
            db_session,
            device_id=device.id,
            reading_type=ReadingType.TEMPERATURE,
            start_date=base_time,
            end_date=base_time + timedelta(minutes=readings_per_type*2)
        )
        
        humid_readings = await crud_reading.get_by_device(
            db_session,
            device_id=device.id,
            reading_type=ReadingType.HUMIDITY,
            start_date=base_time,
            end_date=base_time + timedelta(minutes=readings_per_type*2)
        )
        
        assert all(r.reading_type == ReadingType.TEMPERATURE for r in temp_readings)
        assert all(r.reading_type == ReadingType.HUMIDITY for r in humid_readings)
        assert len(temp_readings) == len(humid_readings)

    async def test_time_window_limits(self, db_session: AsyncSession):
        """Test handling of time window limits."""
        device_in = DeviceCreate(device_id="test-window-limits", name="Test Device")
        device = await crud_device.create(db_session, obj_in=device_in)
        
        # Try to query with a time window larger than 30 days
        start_date = datetime(2024, 1, 1)
        end_date = datetime(2024, 2, 1) + timedelta(days=1)  # 32 days
        
        with pytest.raises(Exception) as exc_info:
            await crud_reading.get_by_device(
                db_session,
                device_id=device.id,
                start_date=start_date,
                end_date=end_date
            )
        assert "Time window too large" in str(exc_info.value)

    async def test_empty_time_periods(self, db_session: AsyncSession):
        """Test handling of time periods with no readings."""
        device_in = DeviceCreate(device_id="test-empty-periods", name="Test Device")
        device = await crud_device.create(db_session, obj_in=device_in)
        
        # Create readings with a gap in the middle
        base_time = datetime(2024, 1, 1, 12, 0)
        
        # First batch of readings
        for i in range(5):
            reading_in = ReadingCreate(
                reading_type=ReadingType.TEMPERATURE,
                value=20.0 + i,
                device_id=device.device_id,
                timestamp=base_time + timedelta(minutes=i)
            )
            await crud_reading.create_with_device(
                db_session,
                obj_in=reading_in,
                device_id=device.id
            )
        
        # Second batch after a 1-hour gap
        for i in range(5):
            reading_in = ReadingCreate(
                reading_type=ReadingType.TEMPERATURE,
                value=25.0 + i,
                device_id=device.device_id,
                timestamp=base_time + timedelta(hours=1, minutes=i)
            )
            await crud_reading.create_with_device(
                db_session,
                obj_in=reading_in,
                device_id=device.id
            )
        
        # Query the gap period
        gap_readings = await crud_reading.get_by_device(
            db_session,
            device_id=device.id,
            start_date=base_time + timedelta(minutes=10),
            end_date=base_time + timedelta(minutes=50)
        )
        
        assert len(gap_readings) == 0
        
        # Query including data before and after gap
        all_readings = await crud_reading.get_by_device(
            db_session,
            device_id=device.id,
            start_date=base_time,
            end_date=base_time + timedelta(hours=2)
        )
        
        assert len(all_readings) == 10
