import pytest
from app.services.user_service import user_service
from app.schemas.user import UserCreateSchema, UserRole
from app.core.database import connect_to_mongo, close_mongo_connection, get_database


@pytest.mark.asyncio
async def test_create_user_success():
    """Test successful user creation"""
    # Skip if MongoDB not available
    try:
        await connect_to_mongo()
    except Exception:
        pytest.skip("MongoDB not available")

    db = get_database()
    if db is None:
        pytest.skip("Database not available")

    # Use a unique username for this test
    test_username = "testuser123_create"
    test_email = "test123_create@example.com"

    try:
        # Clean up any existing test user
        await db.users.delete_many({"username": test_username})
        await db.users.delete_many({"email": test_email})

        # Create test user
        user_data = UserCreateSchema(
            username=test_username,
            email=test_email,
            password="testpassword123",
            role=UserRole.USER
        )

        user = await user_service.create_user(user_data)

        # Verify user properties
        assert user.username == test_username
        assert user.email == test_email
        assert user.role == UserRole.USER
        assert user.is_active is True
        assert user.password_hash != "testpassword123"  # Should be hashed
        assert user._id is not None, f"User _id should not be None. User: {user.__dict__}"

        # Verify user was actually saved to database
        saved_user = await user_service.get_user_by_username(test_username)
        assert saved_user is not None
        assert saved_user._id == user._id

    finally:
        # Clean up
        await db.users.delete_many({"username": test_username})
        await db.users.delete_many({"email": test_email})
        await close_mongo_connection()


@pytest.mark.asyncio
async def test_create_user_duplicate_username():
    """Test user creation with duplicate username"""
    try:
        await connect_to_mongo()
    except Exception:
        pytest.skip("MongoDB not available")
    
    try:
        db = get_database()
        if db is not None:
            await db.users.delete_many({"username": "duplicate_user"})
        
        # Create first user
        user_data1 = UserCreateSchema(
            username="duplicate_user",
            email="user1@example.com",
            password="password123",
            role=UserRole.USER
        )
        await user_service.create_user(user_data1)
        
        # Try to create second user with same username
        user_data2 = UserCreateSchema(
            username="duplicate_user",
            email="user2@example.com",
            password="password456",
            role=UserRole.USER
        )
        
        with pytest.raises(ValueError, match="Username already exists"):
            await user_service.create_user(user_data2)
            
    finally:
        if db is not None:
            await db.users.delete_many({"username": "duplicate_user"})
        await close_mongo_connection()


@pytest.mark.asyncio
async def test_create_user_duplicate_email():
    """Test user creation with duplicate email"""
    try:
        await connect_to_mongo()
    except Exception:
        pytest.skip("MongoDB not available")
    
    try:
        db = get_database()
        if db is not None:
            await db.users.delete_many({"email": "duplicate@example.com"})
        
        # Create first user
        user_data1 = UserCreateSchema(
            username="user1",
            email="duplicate@example.com",
            password="password123",
            role=UserRole.USER
        )
        await user_service.create_user(user_data1)
        
        # Try to create second user with same email
        user_data2 = UserCreateSchema(
            username="user2",
            email="duplicate@example.com",
            password="password456",
            role=UserRole.USER
        )
        
        with pytest.raises(ValueError, match="Email already exists"):
            await user_service.create_user(user_data2)
            
    finally:
        if db is not None:
            await db.users.delete_many({"email": "duplicate@example.com"})
        await close_mongo_connection()


@pytest.mark.asyncio
async def test_get_user_by_username():
    """Test getting user by username"""
    try:
        await connect_to_mongo()
    except Exception:
        pytest.skip("MongoDB not available")
    
    try:
        db = get_database()
        if db is not None:
            await db.users.delete_many({"username": "findme"})
        
        # Create test user
        user_data = UserCreateSchema(
            username="findme",
            email="findme@example.com",
            password="password123",
            role=UserRole.USER
        )
        created_user = await user_service.create_user(user_data)
        
        # Find user
        found_user = await user_service.get_user_by_username("findme")
        
        assert found_user is not None
        assert found_user.username == "findme"
        assert found_user.email == "findme@example.com"
        assert found_user._id == created_user._id
        
        # Test non-existent user
        not_found = await user_service.get_user_by_username("nonexistent")
        assert not_found is None
        
    finally:
        if db is not None:
            await db.users.delete_many({"username": "findme"})
        await close_mongo_connection()
