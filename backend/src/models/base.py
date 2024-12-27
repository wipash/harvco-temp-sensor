"""
Base module for SQLAlchemy models.

This module provides the Base class for all SQLAlchemy models and imports all models
to ensure they are registered with SQLAlchemy.
"""

from typing import Any

from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.orm import DeclarativeBase

class Base(DeclarativeBase):
    """Base class for all SQLAlchemy models."""

    @declared_attr
    def __tablename__(cls) -> str:
        """
        Generate __tablename__ automatically from class name.

        Returns:
            str: Lowercase class name as table name
        """
        return cls.__name__.lower()

    # Convenience methods can be added here
    def dict(self) -> dict[str, Any]:
        """
        Convert model instance to dictionary.

        Returns:
            dict: Model data as dictionary
        """
        return {
            column.name: getattr(self, column.name)
            for column in self.__table__.columns
        }
