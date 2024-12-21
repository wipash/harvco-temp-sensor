from aiomqtt import Client as MQTTClient
from config import Settings
from message_processor import MessageProcessor
import logging
import asyncio
import re
from schemas import ReadingCreate
from datetime import datetime

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

    def parse_device_id(self, topic: str) -> str:
        """Extract device ID from MQTT topic.

        Example: "harvco/harvco-temp-sensor-62ba71/sensor/temperature/state" -> "62ba71"
        """
        pattern = r"harvco/harvco-temp-sensor-([^/]+)/sensor/(?:temperature|humidity)/state"
        match = re.match(pattern, topic)
        if not match:
            raise ValueError(f"Invalid topic format: {topic}")
        return match.group(1)

    def parse_reading_type(self, topic: str) -> str:
        """Extract reading type (temperature or humidity) from topic."""
        pattern = r"harvco/harvco-temp-sensor-[^/]+/sensor/([^/]+)/state"
        match = re.match(pattern, topic)
        if not match:
            raise ValueError(f"Invalid topic format: {topic}")
        return match.group(1)

    async def message_worker(self, client, worker_id: int) -> None:
        """Worker task to process messages concurrently."""
        try:
            async for message in client.messages:
                topic = message.topic.value
                payload = message.payload.decode()
                logger.debug(f"Worker {worker_id}: Received message on topic {topic}: {payload}")

                try:
                    # Extract device ID and reading type from topic
                    device_id = self.parse_device_id(topic)
                    reading_type = self.parse_reading_type(topic)

                    # Parse payload as float, set to None if invalid
                    try:
                        value = float(payload)
                    except ValueError:
                        logger.warning(f"Worker {worker_id}: Non-numeric payload received: {payload}")
                        value = None

                    reading_data = {
                        "device_id": device_id,
                        "reading_type": reading_type,
                        "value": value,
                        "timestamp": datetime.utcnow()
                    }

                    reading = ReadingCreate(**reading_data)

                    if value is not None:  # Only process if we got a valid numeric reading
                        logger.info(f"Worker {worker_id}: Processing {reading_type} reading for device {device_id}")
                        await self.message_processor.process_message(reading)
                        logger.info(f"Worker {worker_id}: Successfully processed {reading_type} reading for device {device_id}")
                    else:
                        logger.warning(f"Worker {worker_id}: Skipping invalid {reading_type} reading for device {device_id}")
                except ValueError as e:
                    logger.error(f"Worker {worker_id}: Topic parsing error: {str(e)}")
                except Exception as e:
                    logger.error(f"Worker {worker_id}: Failed to process message from topic {topic}: {str(e)}")
        except asyncio.CancelledError:
            logger.info(f"Worker {worker_id}: Shutting down")
            raise
        except Exception as e:
            logger.error(f"Worker {worker_id}: Unexpected error: {str(e)}")
            raise

    async def subscribe(self, num_workers: int = 2) -> None:
        """Subscribe to MQTT topics and process incoming messages using multiple workers.

        Args:
            num_workers (int): Number of concurrent message processing workers
        """
        while True:
            try:
                logger.info(
                    "Connecting to MQTT broker at %s:%d",
                    self.settings.MQTT_BROKER_URL,
                    self.settings.MQTT_BROKER_PORT,
                )

                async with MQTTClient(
                    hostname=self.settings.MQTT_BROKER_URL,
                    port=self.settings.MQTT_BROKER_PORT,
                    username=self.settings.MQTT_USERNAME,
                    password=self.settings.MQTT_PASSWORD,
                ) as client:
                    logger.info("Connected to MQTT broker")
                    await client.subscribe(self.settings.MQTT_TOPIC)
                    logger.info("Subscribed to topic %s", self.settings.MQTT_TOPIC)

                    # Use TaskGroup to manage multiple worker tasks
                    async with asyncio.TaskGroup() as tg:
                        for i in range(num_workers):
                            tg.create_task(self.message_worker(client, i))

            except ConnectionError as e:
                logger.error("MQTT connection error: %s", str(e))
            except asyncio.CancelledError:
                logger.info("MQTT client service shutdown requested")
                raise  # Re-raise to allow proper shutdown
            except Exception as e:
                logger.error("Unexpected error in MQTT client: %s", str(e))

            # Wait before reconnection attempt
            logger.info(
                "Waiting %d seconds before reconnection attempt",
                self.settings.RECONNECT_INTERVAL,
            )
            await asyncio.sleep(self.settings.RECONNECT_INTERVAL)
