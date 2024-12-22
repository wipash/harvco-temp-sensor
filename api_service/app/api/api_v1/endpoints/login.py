"""
Login endpoints for authentication.

This module provides endpoints for user authentication and token management.
"""

from datetime import timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status, Cookie
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
import jwt

from app.core.config import settings
from app.core.security import (
    create_access_token,
    create_refresh_token,
    verify_refresh_token,
    REFRESH_TOKEN_EXPIRE_DAYS
)
from app.api.deps import get_db, get_current_active_user
from app.crud import user as crud_user
from app.crud.crud_token import crud_refresh_token
from app.schemas.token import Token, RefreshTokenCreate

router = APIRouter()

@router.post("/login", response_model=Token)
async def login(
    db: Annotated[AsyncSession, Depends(get_db)],
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()]
) -> JSONResponse:
    """
    OAuth2 compatible token login, get an access token and refresh token for future requests.
    """
    user = await crud_user.authenticate(
        db, email=form_data.username, password=form_data.password
    )
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    elif not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )

    # Create access token
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        subject=str(user.id), expires_delta=access_token_expires
    )

    # Create refresh token
    refresh_token, token_id, expires_at = create_refresh_token(user.id)

    # Store refresh token in database
    refresh_token_data = RefreshTokenCreate(
        token_id=token_id,
        user_id=user.id,
        expires_at=expires_at
    )
    await crud_refresh_token.create(db, obj_in=refresh_token_data)
    await db.commit()

    # Create response with tokens
    response = JSONResponse(
        content={
            "access_token": access_token,
            "token_type": "bearer"
        }
    )

    # Set refresh token in HTTP-only cookie
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=True,  # Enable in production with HTTPS
        samesite="lax",
        max_age=REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,  # in seconds
        path="/api/v1/refresh"  # Only sent to refresh endpoint
    )

    return response

@router.post("/refresh", response_model=Token)
async def refresh_token(
    db: Annotated[AsyncSession, Depends(get_db)],
    refresh_token: str = Cookie(None)
) -> dict:
    """
    Get new access token using refresh token.
    """
    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token missing"
        )

    try:
        payload = verify_refresh_token(refresh_token)
        token_id = payload["jti"]
        user_id = int(payload["sub"])
    except (jwt.InvalidTokenError, ValueError) as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e)
        )

    # Verify token exists in database
    db_token = await crud_refresh_token.get_by_token_id(db, token_id=token_id)
    if not db_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )

    # Create new access token
    access_token = create_access_token(subject=user_id)

    return {
        "access_token": access_token,
        "token_type": "bearer"
    }

@router.post("/test-token", response_model=None)
async def test_token(
    current_user = Depends(get_current_active_user)
) -> dict:
    """
    Test access token by returning current user.
    
    Args:
        current_user: Current authenticated user from token
        
    Returns:
        dict: Message confirming token is valid
    """
    return {"msg": "Token is valid", "user_id": current_user.id}
