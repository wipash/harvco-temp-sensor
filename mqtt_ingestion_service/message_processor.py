from shared.models import Device, Reading
from shared.schemas import ReadingCreate


from sqlalchemy.ext.asyncio import AsyncSession
from shared.models import Device, Reading
from sqlalchemy.future import select

class MessageProcessor:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def process_message(self, device_id: str, temperature: float):
        # Check if device exists
        result = await self.session.execute(select(Device).filter_by(device_id=device_id))
        device = result.scalars().first()

        if not device:
            # Create new device
            device = Device(device_id=device_id)
            self.session.add(device)
            await self.session.commit()
            await self.session.refresh(device)

        # Create new reading
        reading = Reading(
            device_id=device.id,
            temperature=temperature
        )
        self.session.add(reading)
        await self.session.commit()
