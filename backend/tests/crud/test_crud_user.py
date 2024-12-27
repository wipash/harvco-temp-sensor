import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from src.api_service.crud.crud_user import user as crud_user
from src.schemas.user import UserCreate, UserUpdate
from src.api_service.core.security import verify_password

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

    async def test_get_multi_with_devices(self, db_session: AsyncSession):
        """Test retrieving users with their associated devices."""
        from src.schemas.device import DeviceCreate
        from src.api_service.crud.crud_device import device as crud_device

        # Create test users
        users = []
        for i in range(3):
            user_in = UserCreate(
                email=f"user{i}@example.com",
                password="password123",
                is_active=True
            )
            user = await crud_user.create(db_session, obj_in=user_in)
            users.append(user)

        # Create devices for first two users
        for user in users[:2]:
            device_in = DeviceCreate(
                device_id=f"device-{user.id}",
                name=f"Test Device for {user.email}",
                is_active=True
            )
            await crud_device.create_with_owner(
                db_session,
                obj_in=device_in,
                owner_id=user.id
            )

        # Test get_multi_with_devices
        users_with_devices = await crud_user.get_multi_with_devices(
            db_session,
            skip=0,
            limit=10
        )

        assert len(users_with_devices) == 3
        assert len(users_with_devices[0].devices) == 1
        assert len(users_with_devices[1].devices) == 1
        assert len(users_with_devices[2].devices) == 0

    async def test_get_devices_for_user(self, db_session: AsyncSession):
        """Test retrieving devices for a specific user."""
        from src.schemas.device import DeviceCreate
        from src.api_service.crud.crud_device import device as crud_device

        # Create test user
        user_in = UserCreate(
            email="devicetest@example.com",
            password="password123",
            is_active=True
        )
        user = await crud_user.create(db_session, obj_in=user_in)

        # Create multiple devices for user
        devices_data = [
            DeviceCreate(
                device_id=f"device-{i}",
                name=f"Device {i}",
                is_active=True
            )
            for i in range(3)
        ]

        for device_in in devices_data:
            await crud_device.create_with_owner(
                db_session,
                obj_in=device_in,
                owner_id=user.id
            )

        # Test getting all devices
        devices = await crud_user.get_devices(
            db_session,
            user_id=user.id,
            active_only=False
        )
        assert len(devices) == 3

        # Test pagination
        paginated_devices = await crud_user.get_devices(
            db_session,
            user_id=user.id,
            skip=1,
            limit=1
        )
        assert len(paginated_devices) == 1

        # Test active_only filter
        # First deactivate one device
        await crud_device.deactivate(db_session, id=devices[0].id)
        active_devices = await crud_user.get_devices(
            db_session,
            user_id=user.id,
            active_only=True
        )
        assert len(active_devices) == 2

    async def test_deactivate_user_cascade(self, db_session: AsyncSession):
        """Test deactivating user and checking impact on related devices."""
        from src.schemas.device import DeviceCreate
        from src.api_service.crud.crud_device import device as crud_device

        # Create user with devices
        user_in = UserCreate(
            email="deactivatetest@example.com",
            password="password123",
            is_active=True
        )
        user = await crud_user.create(db_session, obj_in=user_in)

        # Create device for user
        device_in = DeviceCreate(
            device_id="test-device",
            name="Test Device",
            is_active=True
        )
        device = await crud_device.create_with_owner(
            db_session,
            obj_in=device_in,
            owner_id=user.id
        )

        # Deactivate user
        deactivated_user = await crud_user.deactivate(db_session, user_id=user.id)
        assert not deactivated_user.is_active

        # Check if user can still authenticate
        auth_result = await crud_user.authenticate(
            db_session,
            email=user.email,
            password="password123"
        )
        assert not auth_result

    async def test_update_with_invalid_data(self, db_session: AsyncSession):
        """Test updating user with invalid data."""
        user_in = UserCreate(
            email="invalid@example.com",
            password="password123",
            is_active=True
        )
        user = await crud_user.create(db_session, obj_in=user_in)

        # Test with invalid email format
        with pytest.raises(Exception):  # Adjust exception type based on your validation
            invalid_update = UserUpdate(email="not-an-email")
            await crud_user.update(db_session, db_obj=user, obj_in=invalid_update)

        # Verify user wasn't changed
        unchanged_user = await crud_user.get(db_session, id=user.id)
        assert unchanged_user.email == "invalid@example.com"

    async def test_get_inactive_users(self, db_session: AsyncSession):
        """Test retrieving inactive users."""
        # Create mix of active and inactive users
        users_data = [
            ("active@example.com", True),
            ("inactive1@example.com", False),
            ("inactive2@example.com", False),
        ]

        for email, is_active in users_data:
            user_in = UserCreate(
                email=email,
                password="password123",
                is_active=is_active
            )
            await crud_user.create(db_session, obj_in=user_in)

        # Get all users
        all_users = await crud_user.get_multi(db_session)
        assert len(all_users) == 3

        # Count inactive users
        inactive_users = [user for user in all_users if not user.is_active]
        assert len(inactive_users) == 2

    async def test_superuser_operations(self, db_session: AsyncSession):
        """Test operations specific to superusers."""
        # Create superuser
        super_user_in = UserCreate(
            email="super@example.com",
            password="password123",
            is_active=True,
            is_superuser=True
        )
        super_user = await crud_user.create(db_session, obj_in=super_user_in)

        assert await crud_user.is_superuser(super_user)

        # Test updating superuser status
        update_data = {"is_superuser": False}
        updated_user = await crud_user.update(
            db_session,
            db_obj=super_user,
            obj_in=update_data
        )
        assert not await crud_user.is_superuser(updated_user)

    async def test_get_by_email_not_found(self, db_session: AsyncSession):
        """Test getting a user by email that doesn't exist."""
        non_existent_user = await crud_user.get_by_email(
            db_session,
            email="nonexistent@example.com"
        )
        assert non_existent_user is None

    async def test_create_duplicate_email(self, db_session: AsyncSession):
        """Test creating a user with duplicate email."""
        user_data = {
            "email": "duplicate@example.com",
            "password": "password123",
            "is_active": True
        }

        # Create first user
        user_in = UserCreate(**user_data)
        await crud_user.create(db_session, obj_in=user_in)

        # Attempt to create second user with same email
        with pytest.raises(Exception):  # Adjust exception type based on your DB constraints
            await crud_user.create(db_session, obj_in=user_in)

    async def test_password_update(self, db_session: AsyncSession):
        """Test updating user's password."""
        # Create user
        user_in = UserCreate(
            email="passwordupdate@example.com",
            password="oldpassword123",
            is_active=True
        )
        user = await crud_user.create(db_session, obj_in=user_in)

        # Update password
        new_password = "newpassword123"
        update_data = {"password": new_password}
        updated_user = await crud_user.update(
            db_session,
            db_obj=user,
            obj_in=update_data
        )

        # Verify old password no longer works
        old_auth = await crud_user.authenticate(
            db_session,
            email=user.email,
            password="oldpassword123"
        )
        assert old_auth is None

        # Verify new password works
        new_auth = await crud_user.authenticate(
            db_session,
            email=user.email,
            password=new_password
        )
        assert new_auth is not None
        assert new_auth.id == user.id

    async def test_partial_update(self, db_session: AsyncSession):
        """Test partial update of user attributes."""
        user_in = UserCreate(
            email="partial@example.com",
            password="password123",
            is_active=True,
            is_superuser=False
        )
        user = await crud_user.create(db_session, obj_in=user_in)

        # Update only email
        update_data = {"email": "newemail@example.com"}
        updated_user = await crud_user.update(
            db_session,
            db_obj=user,
            obj_in=update_data
        )

        assert updated_user.email == "newemail@example.com"
        assert updated_user.is_active == user.is_active  # Should remain unchanged
        assert updated_user.is_superuser == user.is_superuser  # Should remain unchanged

    async def test_get_multi_pagination_edge_cases(self, db_session: AsyncSession):
        """Test pagination edge cases for get_multi."""
        # Create 5 users
        for i in range(5):
            user_in = UserCreate(
                email=f"pagination{i}@example.com",
                password="password123",
                is_active=True
            )
            await crud_user.create(db_session, obj_in=user_in)

        # Test zero skip
        users = await crud_user.get_multi(db_session, skip=0, limit=2)
        assert len(users) == 2

        # Test skip > total records
        users = await crud_user.get_multi(db_session, skip=10, limit=2)
        assert len(users) == 0

        # Test large limit
        users = await crud_user.get_multi(db_session, skip=0, limit=1000)
        assert len(users) == 5

    async def test_authenticate_inactive_user(self, db_session: AsyncSession):
        """Test authentication with inactive user."""
        # Create inactive user
        user_in = UserCreate(
            email="inactive@example.com",
            password="password123",
            is_active=False
        )
        user = await crud_user.create(db_session, obj_in=user_in)

        # Attempt authentication
        auth_result = await crud_user.authenticate(
            db_session,
            email=user.email,
            password="password123"
        )
        assert auth_result is None
