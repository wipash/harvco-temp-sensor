from sqlalchemy import Column, Integer, String, ForeignKey
from .base import Base

class Device(Base):
    __tablename__ = 'devices'

    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=True)
    owner_id = Column(Integer, ForeignKey('users.id'), nullable=True)
