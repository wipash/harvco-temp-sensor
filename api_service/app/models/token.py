from datetime import datetime, UTC
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.types import TypeDecorator

from ..db.base import Base

class UTCDateTime(TypeDecorator):
    """Automatically convert naive datetimes to UTC-aware ones"""
    impl = DateTime(timezone=True)  # Changed to use timezone=True
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is not None:
            if value.tzinfo is None:
                value = value.replace(tzinfo=UTC)
            return value.astimezone(UTC)
        return value

    def process_result_value(self, value, dialect):
        if value is not None:
            return value.replace(tzinfo=UTC)
        return value

class RefreshToken(Base):
    """Model for storing refresh tokens"""
    __tablename__ = "refresh_tokens"

    id = Column(Integer, primary_key=True, index=True)
    token_id = Column(String, unique=True, index=True, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    expires_at = Column(UTCDateTime, nullable=False)
    created_at = Column(UTCDateTime, default=lambda: datetime.now(UTC), nullable=False)

    # Relationship to user
    user = relationship("User", back_populates="refresh_tokens")
