from sqlalchemy import Column, Integer, Float, DateTime, ForeignKey, func, String, Enum
from sqlalchemy.orm import relationship
from ..db.base import Base
import enum

class ReadingType(str, enum.Enum):
    TEMPERATURE = "temperature"
    HUMIDITY = "humidity"

class Reading(Base):
    __tablename__ = 'readings'

    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(Integer, ForeignKey('devices.id'), nullable=False)
    reading_type = Column(Enum(ReadingType), nullable=False)
    value = Column(Float, nullable=False)
    timestamp = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    # Relationships
    device = relationship("Device", back_populates="readings")
