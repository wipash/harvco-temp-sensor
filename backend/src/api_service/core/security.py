from datetime import datetime, timedelta
from typing import Any, Optional, Tuple
import uuid
import jwt
from passlib.context import CryptContext

from config import settings

# Configure password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT configuration
ALGORITHM = "HS256"
REFRESH_TOKEN_EXPIRE_DAYS = 30

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
    # Create a new datetime object for now to ensure fresh timestamp
    now = datetime.utcnow()

    if expires_delta is None:
        expires_delta = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    # Calculate expiration from current time
    expire = now + expires_delta

    to_encode = {
        "exp": expire,
        "sub": str(subject),
        "type": "access",
        "iat": now  # Add issued at time
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

def create_refresh_token(
    user_id: int,
    expires_delta: Optional[timedelta] = None
) -> Tuple[str, str, datetime]:
    """
    Create a refresh token with UUID and expiration.

    Args:
        user_id: User ID to create token for
        expires_delta: Optional custom expiration time

    Returns:
        Tuple of (encoded token, token ID, expiration datetime)
    """
    if expires_delta is None:
        expires_delta = timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)

    expire = datetime.utcnow() + expires_delta
    token_id = str(uuid.uuid4())

    to_encode = {
        "exp": expire,
        "sub": str(user_id),
        "type": "refresh",
        "jti": token_id
    }

    encoded_token = jwt.encode(
        to_encode,
        settings.SECRET_KEY,
        algorithm=ALGORITHM
    )

    return encoded_token, token_id, expire

def verify_refresh_token(token: str) -> dict:
    """
    Verify a refresh token and return its payload.

    Args:
        token: Refresh token to verify

    Returns:
        dict: Decoded token payload

    Raises:
        jwt.InvalidTokenError: If token is invalid
        ValueError: If token type is not 'refresh'
    """
    payload = decode_token(token)

    if payload.get("type") != "refresh":
        raise ValueError("Invalid token type")

    if "jti" not in payload:
        raise ValueError("Missing token ID")

    return payload
