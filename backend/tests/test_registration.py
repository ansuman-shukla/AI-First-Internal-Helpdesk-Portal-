import pytest
from fastapi.testclient import TestClient
from fastapi import FastAPI
from app.routers.auth import router as auth_router
from app.core.database import connect_to_mongo, close_mongo_connection, get_database

# Create test app
app = FastAPI()
app.include_router(auth_router)

client = TestClient(app)


@pytest.fixture(scope="function")
async def setup_database():
    """Setup database for tests"""
    try:
        await connect_to_mongo()
        db = get_database()
        if db is not None:
            # Clean up test users before each test
            await db.users.delete_many({"username": {"$regex": "^test"}})
        yield db
    except Exception:
        pytest.skip("MongoDB not available")
    finally:
        if db is not None:
            # Clean up test users after each test
            await db.users.delete_many({"username": {"$regex": "^test"}})
        await close_mongo_connection()


@pytest.mark.asyncio
async def test_register_user_success(setup_database):
    """Test successful user registration"""
    db = setup_database
    if db is None:
        pytest.skip("Database not available")
        
        response = client.post("/auth/register", json={
            "username": "testuser_reg",
            "email": "testuser_reg@example.com",
            "password": "securepassword123",
            "role": "user"
        })
        
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "User registered successfully"
        assert data["username"] == "testuser_reg"
        assert data["email"] == "testuser_reg@example.com"
        assert data["role"] == "user"
        assert "created_at" in data


@pytest.mark.asyncio
async def test_register_admin_user(setup_database):
    """Test registering an admin user"""
    db = setup_database
    if db is None:
        pytest.skip("Database not available")
        
        response = client.post("/auth/register", json={
            "username": "testadmin",
            "email": "testadmin@example.com",
            "password": "adminpassword123",
            "role": "admin"
        })
        
        assert response.status_code == 200
        data = response.json()
        assert data["role"] == "admin"


@pytest.mark.asyncio
async def test_register_duplicate_username(setup_database):
    """Test registration with duplicate username"""
    db = setup_database
    if db is None:
        pytest.skip("Database not available")
        
        # Register first user
        response1 = client.post("/auth/register", json={
            "username": "testduplicate",
            "email": "user1@example.com",
            "password": "password123",
            "role": "user"
        })
        assert response1.status_code == 200
        
        # Try to register second user with same username
        response2 = client.post("/auth/register", json={
            "username": "testduplicate",
            "email": "user2@example.com",
            "password": "password456",
            "role": "user"
        })
        
        assert response2.status_code == 400
        assert "Username already exists" in response2.json()["detail"]


@pytest.mark.asyncio
async def test_register_duplicate_email(setup_database):
    """Test registration with duplicate email"""
    db = setup_database
    if db is None:
        pytest.skip("Database not available")
        
        # Register first user
        response1 = client.post("/auth/register", json={
            "username": "testuser1",
            "email": "testduplicate@example.com",
            "password": "password123",
            "role": "user"
        })
        assert response1.status_code == 200
        
        # Try to register second user with same email
        response2 = client.post("/auth/register", json={
            "username": "testuser2",
            "email": "testduplicate@example.com",
            "password": "password456",
            "role": "user"
        })
        
        assert response2.status_code == 400
        assert "Email already exists" in response2.json()["detail"]


def test_register_invalid_email():
    """Test registration with invalid email format"""
    response = client.post("/auth/register", json={
        "username": "testuser",
        "email": "invalid-email",
        "password": "password123",
        "role": "user"
    })
    
    assert response.status_code == 422  # Validation error


def test_register_missing_fields():
    """Test registration with missing required fields"""
    response = client.post("/auth/register", json={
        "username": "testuser",
        # Missing email and password
        "role": "user"
    })
    
    assert response.status_code == 422  # Validation error


@pytest.mark.asyncio
async def test_login_with_registered_user(setup_database):
    """Test login with a user created via registration"""
    db = setup_database
    if db is None:
        pytest.skip("Database not available")
        
        # Register user
        register_response = client.post("/auth/register", json={
            "username": "testloginuser",
            "email": "testloginuser@example.com",
            "password": "mypassword123",
            "role": "user"
        })
        assert register_response.status_code == 200
        
        # Login with registered user
        login_response = client.post("/auth/login", json={
            "username": "testloginuser",
            "password": "mypassword123"
        })
        
        assert login_response.status_code == 200
        data = login_response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_login_with_wrong_password(setup_database):
    """Test login with wrong password for registered user"""
    db = setup_database
    if db is None:
        pytest.skip("Database not available")
        
        # Register user
        register_response = client.post("/auth/register", json={
            "username": "testwrongpass",
            "email": "testwrongpass@example.com",
            "password": "correctpassword",
            "role": "user"
        })
        assert register_response.status_code == 200
        
        # Try login with wrong password
        login_response = client.post("/auth/login", json={
            "username": "testwrongpass",
            "password": "wrongpassword"
        })
        
        assert login_response.status_code == 401
        assert "Incorrect username or password" in login_response.json()["detail"]
