"""
CRUD operations for User model.

This module implements Create, Read, Update, Delete operations for users using
the repository pattern.
"""

from typing import Optional, List, Any, Dict
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.security import create_password_hash, verify_password
from app.models.user import User
from app.schemas.user import UserCreate, UserUpdate
from app.crud.base import CRUDBase


class CRUDUser(CRUDBase[User, UserCreate, UserUpdate]):
    """
    CRUD operations for User model.
    Inherits basic CRUD operations from CRUDBase.
    """

    async def get(self, db: AsyncSession, id: Any) -> Optional[User]:
        """
        Get a user by ID.

        Args:
            db: Database session
            id: User ID

        Returns:
            Optional[User]: Found user or None
        """
        return await super().get(db, id=id)

    async def get_by_email(self, db: AsyncSession, *, email: str) -> Optional[User]:
        """
        Get a user by email.

        Args:
            db: Database session
            email: User's email address

        Returns:
            Optional[User]: Found user or None
        """
        query = select(User).where(User.email == email)
        result = await db.execute(query)
        return result.scalar_one_or_none()

    async def create(self, db: AsyncSession, *, obj_in: UserCreate) -> User:
        """
        Create a new user.

        Args:
            db: Database session
            obj_in: User creation data

        Returns:
            User: Created user
        """
        db_obj = User(
            email=obj_in.email,
            hashed_password=create_password_hash(obj_in.password),
            is_active=obj_in.is_active,
            is_superuser=obj_in.is_superuser
            if hasattr(obj_in, "is_superuser")
            else False,
        )
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj

    async def update(
        self, db: AsyncSession, *, db_obj: User, obj_in: UserUpdate | Dict[str, Any]
    ) -> User:
        """
        Update a user.

        Args:
            db: Database session
            db_obj: Existing user object
            obj_in: Update data

        Returns:
            User: Updated user
        """
        if isinstance(obj_in, dict):
            update_data = obj_in
        else:
            update_data = obj_in.model_dump(exclude_unset=True)

        if "password" in update_data:
            hashed_password = create_password_hash(update_data["password"])
            del update_data["password"]
            update_data["hashed_password"] = hashed_password

        return await super().update(db, db_obj=db_obj, obj_in=update_data)

    async def authenticate(
        self, db: AsyncSession, *, email: str, password: str
    ) -> Optional[User]:
        """
        Authenticate a user.

        Args:
            db: Database session
            email: User's email
            password: User's password

        Returns:
            Optional[User]: Authenticated user or None
        """
        user = await self.get_by_email(db, email=email)
        if not user:
            return None
        if not verify_password(password, user.hashed_password):
            return None
        if not user.is_active:
            return None
        return user

    async def get_multi_with_devices(
        self,
        db: AsyncSession,
        *,
        skip: int = 0,
        limit: int = 100,
        active_only: bool = True,
    ) -> List[User]:
        """
        Get multiple users with their devices preloaded.

        Args:
            db: Database session
            skip: Number of records to skip
            limit: Maximum number of records to return
            active_only: If True, return only active users

        Returns:
            List[User]: List of users with devices
        """
        query = select(User).options(selectinload(User.devices))

        if active_only:
            query = query.where(User.is_active is True)

        query = query.offset(skip).limit(limit)
        result = await db.execute(query)
        return list(result.scalars().all())

    async def is_active(self, user: User) -> bool:
        """
        Check if user is active.

        Args:
            user: User to check

        Returns:
            bool: True if user is active
        """
        return user.is_active

    async def is_superuser(self, user: User) -> bool:
        """
        Check if user is superuser.

        Args:
            user: User to check

        Returns:
            bool: True if user is superuser
        """
        return bool(
            user.is_superuser
        )  # Explicitly convert to bool and return the actual value

    async def get_devices(
        self,
        db: AsyncSession,
        *,
        user_id: int,
        active_only: bool = True,
        skip: int = 0,
        limit: int = 100,
    ) -> List[Any]:
        """
        Get all devices belonging to a user.

        Args:
            db: Database session
            user_id: User ID
            active_only: If True, return only active devices
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List[Device]: List of user's devices
        """
        from app.models.device import Device
        from sqlalchemy import or_, select
        import logging

        logger = logging.getLogger(__name__)

        logger.debug(
            f"Getting devices for user_id={user_id}, active_only={active_only}, skip={skip}, limit={limit}"
        )

        # Get devices with pagination
        query = select(Device).where(Device.owner_id == user_id)

        if active_only:
            # Include devices where is_active is True OR None
            query = query.where(or_(Device.is_active is True, Device.is_active is None))

        query = query.offset(skip).limit(limit)
        logger.debug(f"Query: {query}")

        result = await db.execute(query)
        devices = list(result.scalars().all())
        logger.debug(f"Found {len(devices)} devices")

        # Ensure is_active is a boolean for each devices
        for device in devices:
            if device.is_active is None:
                device.is_active = True  # Set default value
                await db.commit()  # Save the change to database

        return devices

    async def deactivate(self, db: AsyncSession, *, user_id: int) -> Optional[User]:
        """
        Deactivate a user.

        Args:
            db: Database session
            user_id: User ID

        Returns:
            Optional[User]: Deactivated user or None
        """
        user = await self.get(db, id=user_id)
        if not user:
            return None

        user.is_active = False
        await db.commit()
        await db.refresh(user)
        return user


# Create singleton instance for use across the application
user = CRUDUser(User)
