from pydantic import BaseModel
from datetime import datetime

class ReadingBase(BaseModel):
    temperature: float = None
    humidity: float = None
    timestamp: datetime = None

class ReadingCreate(ReadingBase):
    device_id: int

class ReadingOut(ReadingBase):
    id: int
    device_id: int

    class Config:
        from_attributes = True
