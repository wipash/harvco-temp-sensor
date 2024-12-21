import asyncio
from config import settings
from database import async_session_maker
from message_processor import MessageProcessor
from mqtt_client import MQTTClientService

async def main():
    # Create an async database session
    async with async_session_maker() as session:
        # Initialize the message processor with the session
        message_processor = MessageProcessor(session=session)

        # Initialize the MQTT client service with settings and message processor
        mqtt_service = MQTTClientService(
            settings=settings,
            message_processor=message_processor
        )

        # Start the MQTT subscription
        await mqtt_service.subscribe()

if __name__ == '__main__':
    asyncio.run(main())
