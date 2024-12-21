from pydantic import BaseModel

class DeviceBase(BaseModel):
    device_id: str
    name: str = None

class DeviceCreate(DeviceBase):
    pass

class DeviceOut(DeviceBase):
    id: int
    owner_id: int = None

    class Config:
        orm_mode = True
