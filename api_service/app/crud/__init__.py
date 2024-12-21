"""
CRUD operations package.

This module exports all CRUD operation instances.
"""

from .crud_user import user
from .crud_device import device

__all__ = ["user", "device"]
