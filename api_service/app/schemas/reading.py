from pydantic import BaseModel, Field, validator
from datetime import datetime
from typing import Optional
import math
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
    id: Optional[int] = None  # Make id optional
    device_id: int

    @validator('value')
    def validate_value(cls, v):
        if isinstance(v, float) and (math.isnan(v) or math.isinf(v)):
            return 0.0  # or None, depending on your preference
        return v

    class Config:
        from_attributes = True

class ReadingStatistics(BaseModel):
    """Schema for reading statistics."""
    min: float
    max: float
    avg: float
    count: int
