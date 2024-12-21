import asyncio
from config import settings
from database import AsyncSessionFactory, cleanup_database
from message_processor import MessageProcessor
from mqtt_client import MQTTClientService

async def main():
    try:
        mqtt_service = MQTTClientService(
            settings=settings,
            session_factory=AsyncSessionFactory
        )
        await mqtt_service.subscribe()
    finally:
        await cleanup_database()

if __name__ == '__main__':
    asyncio.run(main())
