"""
Token schemas for authentication.
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel

class Token(BaseModel):
    """Schema for access token response."""
    access_token: str
    token_type: str

class TokenPayload(BaseModel):
    """Schema for token payload."""
    sub: Optional[int] = None
    exp: Optional[datetime] = None
    type: Optional[str] = None
    jti: Optional[str] = None

class RefreshTokenCreate(BaseModel):
    """Schema for creating a refresh token."""
    token_id: str
    user_id: int
    expires_at: datetime

class RefreshTokenDB(RefreshTokenCreate):
    """Schema for refresh token from database."""
    id: int
    created_at: datetime

    class Config:
        from_attributes = True
