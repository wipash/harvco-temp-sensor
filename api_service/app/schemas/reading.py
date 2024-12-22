from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional
from app.models.reading import ReadingType

class ReadingBase(BaseModel):
    """Base Reading schema with common attributes."""
    reading_type: ReadingType
    value: float = Field(..., description="The sensor reading value")
    timestamp: Optional[datetime] = None

class ReadingCreate(ReadingBase):
    """Schema for creating a new reading."""
    device_id: str  # Device IDs come as strings from MQTT

class ReadingUpdate(BaseModel):
    """Schema for updating a reading."""
    value: Optional[float] = None
    timestamp: Optional[datetime] = None

class ReadingOut(ReadingBase):
    """Schema for reading output data."""
    timestamp: datetime

    class Config:
        from_attributes = True

class ReadingStatistics(BaseModel):
    """Schema for reading statistics."""
    min: float
    max: float
    avg: float
    count: int
