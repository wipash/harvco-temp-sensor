from shared.schemas import ReadingCreate
import logging
from sqlalchemy.exc import SQLAlchemyError


from sqlalchemy.ext.asyncio import AsyncSession
from shared.models import Device, Reading
from sqlalchemy.future import select
from datetime import datetime

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
        except SQLAlchemyError as e:
            await self.session.rollback()
            logging.error(f"Database error occurred: {e}")
            raise
        except Exception as e:
            logging.error(f"An unexpected error occurred: {e}")
            raise


        if not device:
            # Create new device
            device = Device(device_id=reading_data.device_id)
            self.session.add(device)
            await self.session.commit()
            await self.session.refresh(device)

        # Create new reading
        if reading_data.timestamp is None:
            reading_data.timestamp = datetime.utcnow()

        logging.info(f"Recording new reading for device ID: {device.id}")
        reading = Reading(
            device_id=device.id,
            temperature=reading_data.temperature,
            timestamp=reading_data.timestamp
        )
        self.session.add(reading)
        await self.session.commit()
