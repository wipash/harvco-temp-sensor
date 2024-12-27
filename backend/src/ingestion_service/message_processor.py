from schemas import ReadingCreate
import logging
from sqlalchemy.exc import SQLAlchemyError


from sqlalchemy.ext.asyncio import AsyncSession
from models import Device, Reading
from sqlalchemy.future import select
from datetime import UTC, datetime

class MessageProcessor:
    def __init__(self, session: AsyncSession) -> None:
        self.session: AsyncSession = session

    async def process_message(self, reading_data: ReadingCreate) -> None:
        try:
            logging.info(f"Processing message for device ID: {reading_data.device_id}")
            # Check if device exists
            result = await self.session.execute(select(Device).filter_by(device_id=reading_data.device_id))
            device = result.scalars().first()

            if not device:
                logging.info(f"Creating new device with ID: {reading_data.device_id}")
                device = Device(device_id=reading_data.device_id)
                self.session.add(device)
                await self.session.commit()

            if reading_data.value is not None:
                if reading_data.timestamp is None:
                    reading_data.timestamp = datetime.now(UTC)

                logging.info(f"Recording new {reading_data.reading_type} reading for device ID: {device.id}")
                reading = Reading(
                    device_id=device.id,
                    reading_type=reading_data.reading_type,
                    value=reading_data.value,
                    timestamp=reading_data.timestamp
                )
                self.session.add(reading)
                await self.session.commit()
            else:
                logging.warning(f"Skipping reading creation - no valid {reading_data.reading_type} data")

        except SQLAlchemyError as e:
            await self.session.rollback()
            logging.error(f"Database error occurred: {e}")
            raise
        except Exception as e:
            await self.session.rollback()
            logging.error(f"An unexpected error occurred: {e}")
            raise
