"""
Base CRUD class with default implementations for common operations.
"""

from typing import Any, Dict, Generic, List, Optional, Type, TypeVar, Union
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import Base

ModelType = TypeVar("ModelType", bound=Base)
CreateSchemaType = TypeVar("CreateSchemaType", bound=BaseModel)
UpdateSchemaType = TypeVar("UpdateSchemaType", bound=BaseModel)

class CRUDBase(Generic[ModelType, CreateSchemaType, UpdateSchemaType]):
    """
    Base class for CRUD operations.
    """

    def __init__(self, model: Type[ModelType]):
        """
        Initialize CRUD object with SQLAlchemy model.
        
        Args:
            model: The SQLAlchemy model class
        """
        self.model = model

    async def get(
        self,
        db: AsyncSession,
        id: Any
    ) -> Optional[ModelType]:
        """
        Get a record by ID.

        Args:
            db: Database session
            id: Record ID

        Returns:
            Optional[ModelType]: Found record or None
        """
        query = select(self.model).where(self.model.id == id)
        result = await db.execute(query)
        return result.scalar_one_or_none()

    async def get_multi(
        self,
        db: AsyncSession,
        *,
        skip: int = 0,
        limit: int = 100
    ) -> List[ModelType]:
        """
        Get multiple records.

        Args:
            db: Database session
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List[ModelType]: List of records
        """
        query = select(self.model).offset(skip).limit(limit)
        result = await db.execute(query)
        return list(result.scalars().all())

    async def create(
        self,
        db: AsyncSession,
        *,
        obj_in: CreateSchemaType
    ) -> ModelType:
        """
        Create a new record.

        Args:
            db: Database session
            obj_in: Creation data

        Returns:
            ModelType: Created record
        """
        obj_in_data = obj_in.model_dump(exclude={'id'})
        db_obj = self.model(**obj_in_data)
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj

    async def update(
        self,
        db: AsyncSession,
        *,
        db_obj: ModelType,
        obj_in: Union[UpdateSchemaType, Dict[str, Any]]
    ) -> ModelType:
        """
        Update a record.

        Args:
            db: Database session
            db_obj: Database object to update
            obj_in: Update data

        Returns:
            ModelType: Updated record
        """
        obj_data = db_obj.dict()
        if isinstance(obj_in, dict):
            update_data = obj_in
        else:
            update_data = obj_in.model_dump(exclude_unset=True)
        
        for field in obj_data:
            if field in update_data:
                setattr(db_obj, field, update_data[field])
        
        await db.commit()
        await db.refresh(db_obj)
        return db_obj

    async def remove(
        self,
        db: AsyncSession,
        *,
        id: int
    ) -> Optional[ModelType]:
        """
        Delete a record.

        Args:
            db: Database session
            id: Record ID

        Returns:
            Optional[ModelType]: Deleted record or None
        """
        obj = await self.get(db, id)
        if obj:
            await db.delete(obj)
            await db.commit()
        return obj
