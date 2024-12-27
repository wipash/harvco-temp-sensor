from sqlalchemy import Column, Integer, String, ForeignKey, Boolean, Float
from sqlalchemy.orm import relationship
from .base import Base

class Device(Base):
    __tablename__ = 'devices'

    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=True)
    owner_id = Column(Integer, ForeignKey('users.id'), nullable=True)
    is_active = Column(Boolean, default=True)
    temperature_offset = Column(Float, nullable=True, server_default='0.0')
    humidity_offset = Column(Float, nullable=True, server_default='0.0')

    # Relationships
    readings = relationship("Reading", back_populates="device")
    owner = relationship("User", back_populates="devices")
