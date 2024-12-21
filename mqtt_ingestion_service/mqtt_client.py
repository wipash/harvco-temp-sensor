from asyncio_mqtt import Client as MQTTClient
from config import Settings
from message_processor import MessageProcessor
import logging
import asyncio

logger = logging.getLogger(__name__)

class MQTTClientService:
    """Service for managing MQTT connections and processing messages."""
    def __init__(self, settings: Settings, message_processor: MessageProcessor) -> None:
            """Initialize the MQTTClientService.

            Args:
                settings (Settings): Configuration settings.
                message_processor (MessageProcessor): Processor for handling incoming messages.
            """
        self.settings = settings
        self.message_processor = message_processor

    async def subscribe(self) -> None:
            """Subscribe to MQTT topics and process incoming messages."""
            while True:
                try:
                logger.info("Connecting to MQTT broker at %s:%d", self.settings.MQTT_BROKER_URL, self.settings.MQTT_BROKER_PORT)
                async with MQTTClient(
                    hostname=self.settings.MQTT_BROKER_URL,
                    port=self.settings.MQTT_BROKER_PORT,
                    username=self.settings.MQTT_USERNAME,
                    password=self.settings.MQTT_PASSWORD,
                ) as client:
            logger.info("Connected to MQTT broker")
            await client.subscribe(self.settings.MQTT_TOPIC)
            logger.info("Subscribed to topic %s", self.settings.MQTT_TOPIC)
            async with client.unfiltered_messages() as messages:
                try:
                    async for message in messages:
                    topic = message.topic
                    payload = message.payload.decode()
                    logger.debug("Received message on topic %s: %s", topic, payload)
                    try:
                        logger.info("Processing message from topic %s", topic)
                        await self.message_processor.process_message(topic, payload)
                        logger.info("Successfully processed message from topic %s", topic)
                    except Exception as e:
                        logger.error("Failed to process message from topic %s: %s", topic, str(e))
