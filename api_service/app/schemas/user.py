from typing import Optional
from pydantic import BaseModel, EmailStr

class UserBase(BaseModel):
    """Base User schema with common attributes."""
    email: EmailStr
    is_active: Optional[bool] = True
    is_superuser: Optional[bool] = False

class UserCreate(UserBase):
    """Schema for creating a new user."""
    password: str

class UserUpdate(BaseModel):
    """Schema for updating a user."""
    email: Optional[EmailStr] = None
    password: Optional[str] = None
    is_active: Optional[bool] = None
    is_superuser: Optional[bool] = None

class UserOut(UserBase):
    """Schema for user output data."""
    id: int

    class Config:
        from_attributes = True

class UserWithDevices(UserOut):
    """Schema for user output data including devices."""
    devices: list["DeviceOut"] = []

    class Config:
        from_attributes = True
