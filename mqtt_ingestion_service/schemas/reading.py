from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional

class ReadingBase(BaseModel):
    temperature: Optional[float] = None
    humidity: Optional[float] = None
    timestamp: datetime = None

class ReadingCreate(ReadingBase):
    device_id: str  # Change to str since device IDs come as strings from MQTT

class ReadingOut(ReadingBase):
    id: int
    device_id: int

    class Config:
        from_attributes = True
