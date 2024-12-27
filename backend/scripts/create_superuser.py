"""
Script to create a superuser.

Usage:
    python -m scripts.create_superuser email@example.com password123
"""

import sys
import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from db import get_session
from api_service.crud import user as crud_user
from schemas.user import UserCreate

async def create_superuser(email: str, password: str) -> None:
    """Create a superuser with the given email and password."""
    user_in = UserCreate(
        email=email,
        password=password,
        is_superuser=True,
        is_active=True
    )

    async for db in get_session():
        db: AsyncSession

        # Check if user already exists
        existing_user = await crud_user.get_by_email(db, email=email)
        if existing_user:
            print(f"User with email {email} already exists")
            return

        try:
            user = await crud_user.create(db, obj_in=user_in)
            print(f"Superuser created successfully: {user.email}")
        except Exception as e:
            print(f"Error creating superuser: {str(e)}")
            raise

def main() -> None:
    """Main function to run the script."""
    if len(sys.argv) != 3:
        print("Usage: python -m scripts.create_superuser email@example.com password123")
        sys.exit(1)

    email = sys.argv[1]
    password = sys.argv[2]

    asyncio.run(create_superuser(email, password))

if __name__ == "__main__":
    main()
