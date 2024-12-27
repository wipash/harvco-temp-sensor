"""
Tests for the Config class in config.py to verify correct loading of environment variables.
"""

import pytest
from pydantic import ValidationError
from src.config import Settings

def test_config_loading_from_env(monkeypatch):
    """Test that Config loads values correctly from environment variables."""
    # Set up mock environment variables
    monkeypatch.setenv('MQTT_BROKER_HOST', 'test_mqtt_host')
    monkeypatch.setenv('MQTT_BROKER_PORT', '8883')
    monkeypatch.setenv('MQTT_USERNAME', 'test_user')
    monkeypatch.setenv('MQTT_PASSWORD', 'test_password')
    monkeypatch.setenv('DATABASE_URL', 'postgresql://user:pass@localhost/testdb')

    # Instantiate the Config class
    config = Settings()

    # Assert that the configuration values are as expected
    assert config.mqtt_broker_host == 'test_mqtt_host'
    assert config.mqtt_broker_port == 8883
    assert config.mqtt_username == 'test_user'
    assert config.mqtt_password == 'test_password'
    assert config.database_url == 'postgresql://user:pass@localhost/testdb'

def test_config_default_values(monkeypatch):
    """Test that Config uses default values when environment variables are missing."""
    # Set up mock environment variables without MQTT_BROKER_PORT
    monkeypatch.setenv('MQTT_BROKER_HOST', 'test_mqtt_host')
    monkeypatch.delenv('MQTT_BROKER_PORT', raising=False)
    monkeypatch.setenv('MQTT_USERNAME', 'test_user')
    monkeypatch.setenv('MQTT_PASSWORD', 'test_password')
    monkeypatch.setenv('DATABASE_URL', 'postgresql://user:pass@localhost/testdb')

    # Instantiate the Config class
    config = Settings()

    # Assert that the default port is used
    assert config.mqtt_broker_port == 1883

def test_config_missing_required_env_vars(monkeypatch):
    """Test that Config raises ValidationError when required environment variables are missing."""
    # Remove a required environment variable
    monkeypatch.delenv('MQTT_BROKER_HOST', raising=False)
    monkeypatch.setenv('MQTT_USERNAME', 'test_user')
    monkeypatch.setenv('MQTT_PASSWORD', 'test_password')
    monkeypatch.setenv('DATABASE_URL', 'postgresql://user:pass@localhost/testdb')

    # Attempt to instantiate the Config class and expect a ValidationError
    with pytest.raises(ValidationError):
        Settings()
