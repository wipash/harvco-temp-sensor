from sqlalchemy import Column, Integer, Float, DateTime, ForeignKey, func
from .base import Base

class Reading(Base):
    __tablename__ = 'readings'

    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(Integer, ForeignKey('devices.id'), nullable=False)
    temperature = Column(Float, nullable=False)
    timestamp = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
