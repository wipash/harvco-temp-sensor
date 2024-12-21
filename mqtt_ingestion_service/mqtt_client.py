from asyncio_mqtt import Client as MQTTClient
from config import Settings
from message_processor import MessageProcessor

class MQTTClientService:
    def __init__(self, settings: Settings, message_processor: MessageProcessor):
        self.settings = settings
        self.message_processor = message_processor

    async def subscribe(self):
        async with MQTTClient(
            hostname=self.settings.MQTT_BROKER_URL,
            port=self.settings.MQTT_BROKER_PORT,
            username=self.settings.MQTT_USERNAME,
            password=self.settings.MQTT_PASSWORD,
        ) as client:
            await client.subscribe(self.settings.MQTT_TOPIC)
            async with client.unfiltered_messages() as messages:
                async for message in messages:
                    topic = message.topic
                    payload = message.payload.decode()
                    await self.message_processor.process_message(topic, payload)
