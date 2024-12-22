import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from app.crud.crud_user import user as crud_user
from app.schemas.user import UserCreate, UserUpdate
from app.core.security import verify_password

pytestmark = pytest.mark.asyncio

class TestUserCRUD:
    async def test_create_user(self, db_session: AsyncSession, user_create_data):
        user_in = UserCreate(**user_create_data)
        user = await crud_user.create(db_session, obj_in=user_in)
        
        assert user.email == user_create_data["email"]
        assert user.is_active == user_create_data["is_active"]
        assert user.is_superuser == user_create_data["is_superuser"]
        assert verify_password(user_create_data["password"], user.hashed_password)

    async def test_authenticate_user(self, db_session: AsyncSession, user_create_data):
        # First create a user
        user_in = UserCreate(**user_create_data)
        user = await crud_user.create(db_session, obj_in=user_in)
        
        # Test successful authentication
        authenticated_user = await crud_user.authenticate(
            db_session,
            email=user_create_data["email"],
            password=user_create_data["password"]
        )
        assert authenticated_user
        assert authenticated_user.id == user.id
        
        # Test failed authentication
        wrong_password_user = await crud_user.authenticate(
            db_session,
            email=user_create_data["email"],
            password="wrongpassword"
        )
        assert not wrong_password_user

    async def test_get_user(self, db_session: AsyncSession, user_create_data):
        user_in = UserCreate(**user_create_data)
        created_user = await crud_user.create(db_session, obj_in=user_in)
        
        fetched_user = await crud_user.get(db_session, id=created_user.id)
        assert fetched_user
        assert fetched_user.id == created_user.id
        assert fetched_user.email == created_user.email

    async def test_update_user(self, db_session: AsyncSession, user_create_data):
        # Create user
        user_in = UserCreate(**user_create_data)
        user = await crud_user.create(db_session, obj_in=user_in)
        
        # Update user
        new_email = "updated@example.com"
        user_update = UserUpdate(email=new_email)
        updated_user = await crud_user.update(
            db_session,
            db_obj=user,
            obj_in=user_update
        )
        
        assert updated_user.email == new_email
        assert updated_user.id == user.id

    async def test_delete_user(self, db_session: AsyncSession, user_create_data):
        # Create user
        user_in = UserCreate(**user_create_data)
        user = await crud_user.create(db_session, obj_in=user_in)
        
        # Deactivate user
        deactivated_user = await crud_user.deactivate(db_session, user_id=user.id)
        assert not deactivated_user.is_active
        
        # Verify user is deactivated but still exists
        fetched_user = await crud_user.get(db_session, id=user.id)
        assert fetched_user
        assert not fetched_user.is_active

    async def test_get_multi_users(self, db_session: AsyncSession):
        # Create multiple users
        users_data = [
            {"email": f"user{i}@example.com", "password": "password123"}
            for i in range(3)
        ]
        
        created_users = []
        for user_data in users_data:
            user_in = UserCreate(**user_data)
            user = await crud_user.create(db_session, obj_in=user_in)
            created_users.append(user)
        
        # Test pagination
        users = await crud_user.get_multi(db_session, skip=0, limit=2)
        assert len(users) == 2
        
        users = await crud_user.get_multi(db_session, skip=2, limit=2)
        assert len(users) == 1
