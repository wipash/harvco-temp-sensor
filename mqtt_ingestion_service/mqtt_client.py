from aiomqtt import Client as MQTTClient
from config import Settings
from message_processor import MessageProcessor
import logging
import asyncio
from typing import List
from contextlib import asynccontextmanager

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

    async def message_worker(self, client, worker_id: int) -> None:
        """Worker task to process messages concurrently."""
        try:
            async for message in client.messages:
                topic = message.topic.value
                payload = message.payload.decode()
                logger.debug(f"Worker {worker_id}: Received message on topic {topic}: {payload}")
                
                try:
                    logger.info(f"Worker {worker_id}: Processing message from topic {topic}")
                    await self.message_processor.process_message(topic, payload)
                    logger.info(f"Worker {worker_id}: Successfully processed message from topic {topic}")
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
                logger.info("Connecting to MQTT broker at %s:%d",
                           self.settings.MQTT_BROKER_URL,
                           self.settings.MQTT_BROKER_PORT)

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
            logger.info("Waiting %d seconds before reconnection attempt",
                       self.settings.RECONNECT_INTERVAL)
            await asyncio.sleep(self.settings.RECONNECT_INTERVAL)
