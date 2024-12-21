"""
Configuration management for the MQTT Ingestion Service.

This module defines the Config class, which loads configuration from environment variables.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
from typing import Optional

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8')
    # MQTT broker configuration
    MQTT_BROKER_URL: str = Field(...)

    MQTT_BROKER_PORT: int = Field(default=1883)
    MQTT_USERNAME: Optional[str] = Field(default=None)
    MQTT_PASSWORD: Optional[str] = Field(default=None)
    MQTT_TOPIC: str = Field(default='harvco/+/sensor/+/state')

    # Database Settings
    DATABASE_URL: str = Field(...)

    # Logging Settings
    LOG_LEVEL: str = Field(default='INFO')

    # SQLAlchemy Settings
    SQLALCHEMY_ECHO: bool = Field(default=False, description="Enable SQLAlchemy echo for debugging SQL queries")
    RECONNECT_INTERVAL: int = Field(default=5, description="Interval in seconds before reconnecting after a connection loss")

settings = Settings()
