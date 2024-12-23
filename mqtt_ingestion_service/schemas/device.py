from typing import Optional
from pydantic import BaseModel

class DeviceBase(BaseModel):
    device_id: str
    name: Optional[str] = None
    is_active: Optional[bool] = True  # Make it optional with a default

class DeviceCreate(DeviceBase):
    pass

class DeviceUpdate(BaseModel):
    name: Optional[str] = None
    is_active: Optional[bool] = None

class DeviceOut(DeviceBase):
    id: int
    owner_id: Optional[int] = None
    is_active: bool = True  # Add explicit default here

    class Config:
        from_attributes = True
