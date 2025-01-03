from aiomqtt import Client as MQTTClient
from config import Settings
from ingestion_service.message_processor import MessageProcessor
import logging
import asyncio
import re
from schemas import ReadingCreate
from datetime import UTC, datetime

logger = logging.getLogger(__name__)


class MQTTClientService:
    """Service for managing MQTT connections and processing messages."""

    def __init__(self, settings: Settings, session_factory) -> None:
        """Initialize the MQTTClientService.

        Args:
            settings (Settings): Configuration settings.
            session_factory: AsyncSession factory function
        """
        self.settings = settings
        self.session_factory = session_factory

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
        if "temperature" in topic:
            return "temperature"
        elif "humidity" in topic:
            return "humidity"
        else:
            # Skip other topics like _devicename
            raise ValueError(f"Invalid topic format: {topic}")

    async def message_worker(self, client, worker_id: int) -> None:
        """Worker task to process messages concurrently."""
        async with self.session_factory() as session:
            message_processor = MessageProcessor(session=session)
            try:
                async for message in client.messages:
                    topic = message.topic.value
                    payload = message.payload.decode()
                    logger.debug(f"Worker {worker_id}: Received message on topic {topic}: {payload}")

                    try:
                        # Extract device ID and reading type from topic
                        device_id = self.parse_device_id(topic)
                        try:
                            reading_type = self.parse_reading_type(topic)
                        except ValueError:
                            # Skip non-reading topics (like _devicename) - log as debug since this is expected
                            logger.debug(f"Worker {worker_id}: Skipping non-reading topic: {topic}")
                            continue

                        # Parse payload as float, set to None if invalid or NaN
                        try:
                            if payload.lower() == 'nan':
                                logger.debug(f"Worker {worker_id}: Skipping NaN value from {topic}")
                                value = None
                            else:
                                value = float(payload)
                                if value != value:  # Additional NaN check for float values
                                    logger.debug(f"Worker {worker_id}: Skipping NaN value from {topic}")
                                    value = None
                        except ValueError:
                            logger.debug(f"Worker {worker_id}: Non-numeric payload received: {payload}")
                            value = None

                        reading_data = {
                            "device_id": device_id,
                            "reading_type": reading_type,
                            "value": value,
                            "timestamp": datetime.now(UTC)
                        }

                        try:
                            reading = ReadingCreate(**reading_data)
                            if value is not None:  # Only process if we got a valid numeric reading
                                logger.info(f"Worker {worker_id}: Processing {reading_type} reading for device {device_id}")
                                await message_processor.process_message(reading)
                                logger.info(f"Worker {worker_id}: Successfully processed {reading_type} reading for device {device_id}")
                            else:
                                logger.debug(f"Worker {worker_id}: Skipping invalid {reading_type} reading for device {device_id}")
                        except ValueError as e:
                            logger.debug(f"Worker {worker_id}: Skipping invalid reading data: {str(e)}")

                    except ValueError as e:
                        # Only log as error if it's an unexpected topic format
                        if "_devicename" in topic:
                            logger.debug(f"Worker {worker_id}: Skipping devicename topic: {topic}")
                        else:
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
