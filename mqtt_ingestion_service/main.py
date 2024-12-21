import asyncio
from config import settings
from database import AsyncSessionFactory, cleanup_database
from message_processor import MessageProcessor
from mqtt_client import MQTTClientService

async def main():
    try:
        async with AsyncSessionFactory() as session:
            message_processor = MessageProcessor(session=session)
            mqtt_service = MQTTClientService(
                settings=settings,
                message_processor=message_processor
            )
            await mqtt_service.subscribe()
    finally:
        await cleanup_database()

if __name__ == '__main__':
    asyncio.run(main())
