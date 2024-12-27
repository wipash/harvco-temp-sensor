from typing import Optional
from pydantic import BaseModel, Field, validator

class DeviceBase(BaseModel):
    device_id: str
    name: Optional[str] = None
    is_active: Optional[bool] = True
    temperature_offset: Optional[float] = Field(0.0, ge=-10.0, le=10.0)  # Between -10 and +10
    humidity_offset: Optional[float] = Field(0.0, ge=-20.0, le=20.0)     # Between -20 and +20

    @validator('temperature_offset')
    def validate_temperature_offset(cls, v):
        if v is not None and (v < -10.0 or v > 10.0):
            raise ValueError('Temperature offset must be between -10.0 and +10.0')
        return v

    @validator('humidity_offset')
    def validate_humidity_offset(cls, v):
        if v is not None and (v < -20.0 or v > 20.0):
            raise ValueError('Humidity offset must be between -20.0 and +20.0')
        return v

class DeviceCreate(DeviceBase):
    pass

class DeviceUpdate(BaseModel):
    name: Optional[str] = None
    is_active: Optional[bool] = None
    temperature_offset: Optional[float] = Field(None, ge=-10.0, le=10.0)
    humidity_offset: Optional[float] = Field(None, ge=-20.0, le=20.0)

    @validator('temperature_offset')
    def validate_temperature_offset(cls, v):
        if v is not None and (v < -10.0 or v > 10.0):
            raise ValueError('Temperature offset must be between -10.0 and +10.0')
        return v

    @validator('humidity_offset')
    def validate_humidity_offset(cls, v):
        if v is not None and (v < -20.0 or v > 20.0):
            raise ValueError('Humidity offset must be between -20.0 and +20.0')
        return v

class DeviceOut(DeviceBase):
    id: int
    owner_id: Optional[int] = None
    is_active: bool = True

    class Config:
        from_attributes = True
