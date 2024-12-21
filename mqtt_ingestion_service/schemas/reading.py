from pydantic import BaseModel
from datetime import datetime
from typing import Optional
from models.reading import ReadingType

class ReadingBase(BaseModel):
    reading_type: ReadingType
    value: float
    timestamp: Optional[datetime] = None

class ReadingCreate(ReadingBase):
    device_id: str  # Device IDs come as strings from MQTT

class ReadingOut(ReadingBase):
    id: int
    device_id: int

    class Config:
        from_attributes = True
