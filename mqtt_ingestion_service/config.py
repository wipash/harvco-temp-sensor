"""
Configuration management for the MQTT Ingestion Service.

This module defines the Config class, which loads configuration from environment variables.
"""

from pydantic import BaseSettings

class Config(BaseSettings):
    # MQTT broker configuration
    mqtt_broker_host: str
    mqtt_broker_port: int = 1883  # Default MQTT port
    mqtt_username: str
    mqtt_password: str

    # Database configuration
    database_url: str

    class Config:
        env_file = '.env'  # Specifies the environment file

config = Config()
