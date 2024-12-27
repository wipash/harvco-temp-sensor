"""
Configuration management for the API server.

This module defines the Config class, which loads configuration from environment variables.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8')

    API_V1_STR: str = "/api/v1"
    SECRET_KEY: str = Field(..., env="SECRET_KEY")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days
    DATABASE_URL: str = Field(..., env="DATABASE_URL")

    # Logging Settings
    LOG_LEVEL: str = Field(default='INFO')


    # CORS settings if needed
    BACKEND_CORS_ORIGINS: list[str] = ["http://localhost:3000", "https://sensors.harvco.nz"]

    SQLALCHEMY_ECHO: bool = Field(default=False, description="Enable SQLAlchemy echo for debugging SQL queries")


settings = Settings()
