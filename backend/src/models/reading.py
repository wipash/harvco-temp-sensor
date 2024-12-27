from sqlalchemy import Column, Integer, Float, DateTime, ForeignKey, func, Enum
from sqlalchemy.orm import relationship
from .base import Base
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

    def get_adjusted_value(self) -> float:
        """
        Get the reading value adjusted by the device's offset.
        
        Returns:
            float: The adjusted reading value
        """
        if self.reading_type == ReadingType.TEMPERATURE:
            return self.value + (self.device.temperature_offset or 0.0)
        elif self.reading_type == ReadingType.HUMIDITY:
            return self.value + (self.device.humidity_offset or 0.0)
        return self.value
