"""
API router configuration.

This module configures all API routes for version 1 of the API.
"""

from fastapi import APIRouter

from api_service.api.api_v1.endpoints import users, devices, readings, login

# Create main API router
api_router = APIRouter()

# Include login router
api_router.include_router(
    login.router,
    prefix="/auth",
    tags=["authentication"]
)

# Include other endpoint routers
api_router.include_router(
    users.router,
    prefix="/users",
    tags=["users"]
)

api_router.include_router(
    devices.router,
    prefix="/devices",
    tags=["devices"]
)

api_router.include_router(
    readings.router,
    prefix="/readings",
    tags=["readings"]
)

# If you have an auth router, include it like this:
# api_router.include_router(
#     auth.router,
#     prefix="/auth",
#     tags=["authentication"]
# )
