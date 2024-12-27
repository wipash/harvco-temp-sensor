import asyncio
import logging
import sys
from config import settings
from backend.database import AsyncSessionFactory, cleanup_database
from message_processor import MessageProcessor
from mqtt_client import MQTTClientService

def setup_logging():
    """Configure logging with proper formatting and level from settings."""
    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(settings.LOG_LEVEL.upper())

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # Set levels for specific loggers
    logging.getLogger("aiomqtt").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)

    # Create logger for this module
    logger = logging.getLogger(__name__)
    logger.info(f"Logging configured with level: {settings.LOG_LEVEL.upper()}")

    return logger

async def main():
    logger = setup_logging()

    try:
        logger.info("Starting MQTT ingestion service")
        mqtt_service = MQTTClientService(
            settings=settings,
            session_factory=AsyncSessionFactory
        )
        logger.info("MQTT service initialized, starting subscription")
        await mqtt_service.subscribe()
    except Exception as e:
        logger.error(f"Fatal error in main loop: {str(e)}", exc_info=True)
        raise
    finally:
        logger.info("Cleaning up database connections")
        await cleanup_database()
        logger.info("Shutdown complete")

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nShutdown requested... exiting")
    except Exception:
        logging.getLogger(__name__).exception("Fatal error in main")
        sys.exit(1)
