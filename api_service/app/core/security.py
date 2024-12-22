from datetime import datetime, timedelta
from typing import Any, Optional

import jwt
from passlib.context import CryptContext

from app.core.config import settings

# Configure password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT configuration
ALGORITHM = "HS256"

def create_password_hash(password: str) -> str:
    """
    Hash a password using bcrypt.

    Args:
        password: Plain text password

    Returns:
        Hashed password string

    Raises:
        ValueError: If password is empty, too short, or doesn't meet complexity requirements
    """
    if not password:
        raise ValueError("Password cannot be empty")
    if password.isspace():
        raise ValueError("Password cannot be only whitespace")
    if len(password) < 8:
        raise ValueError("Password must be at least 8 characters")

    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a password against its hash.

    Args:
        plain_password: Password to verify
        hashed_password: Stored hash to check against

    Returns:
        True if password matches, False otherwise
    """
    return pwd_context.verify(plain_password, hashed_password)

def create_access_token(
    subject: Any,
    expires_delta: Optional[timedelta] = None
) -> str:
    """
    Create a JWT access token.

    Args:
        subject: Token subject (typically user_id)
        expires_delta: Optional custom expiration time

    Returns:
        Encoded JWT token string
    """
    if expires_delta is None:
        expires_delta = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    expire = datetime.utcnow() + expires_delta

    to_encode = {
        "exp": expire,
        "sub": str(subject),
        "type": "access"
    }

    return jwt.encode(
        to_encode,
        settings.SECRET_KEY,
        algorithm=ALGORITHM
    )

def decode_token(
    token: str,
    verify_exp: bool = True
) -> dict:
    """
    Decode and verify a JWT token.

    Args:
        token: JWT token to decode
        verify_exp: Whether to verify token expiration

    Returns:
        Decoded token payload

    Raises:
        JWTError: If token is invalid or expired
    """
    return jwt.decode(
        token,
        settings.SECRET_KEY,
        algorithms=[ALGORITHM],
        options={"verify_exp": verify_exp}
    )
