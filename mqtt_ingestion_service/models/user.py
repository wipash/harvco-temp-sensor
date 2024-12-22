from sqlalchemy import Column, Integer, String, Boolean
from sqlalchemy.orm import relationship
from ..db.base import Base

class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    is_superuser = Column(Boolean, default=False)

    # Relationships
    devices = relationship("Device", back_populates="owner")
    refresh_tokens = relationship("RefreshToken", back_populates="user")
