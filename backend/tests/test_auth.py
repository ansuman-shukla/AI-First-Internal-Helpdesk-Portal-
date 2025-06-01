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
async def setup_test_users():
    """Setup test users for authentication tests"""
    try:
        await connect_to_mongo()
        db = get_database()
        if db is not None:
            # Clean up existing test users
            await db.users.delete_many({"username": {"$in": ["testuser", "testadmin"]}})

            # Create test users via registration endpoint
            client.post("/auth/register", json={
                "username": "testuser",
                "email": "testuser@example.com",
                "password": "testpass",
                "role": "user"
            })

            client.post("/auth/register", json={
                "username": "testadmin",
                "email": "testadmin@example.com",
                "password": "adminpass",
                "role": "admin"
            })

        yield db
    except Exception:
        pytest.skip("MongoDB not available")
    finally:
        if db is not None:
            # Clean up test users
            await db.users.delete_many({"username": {"$in": ["testuser", "testadmin"]}})
        await close_mongo_connection()


@pytest.mark.asyncio
async def test_login_success(setup_test_users):
    """Test successful login with valid credentials"""
    db = setup_test_users
    if db is None:
        pytest.skip("Database not available")

        response = client.post("/auth/login", json={
            "username": "testuser",
            "password": "testpass"
        })
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_login_admin_success(setup_test_users):
    """Test successful login with admin credentials"""
    db = setup_test_users
    if db is None:
        pytest.skip("Database not available")

        response = client.post("/auth/login", json={
            "username": "testadmin",
            "password": "adminpass"
        })
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"


def test_login_failure():
    """Test login failure with invalid credentials"""
    response = client.post("/auth/login", json={
        "username": "wronguser",
        "password": "wrongpass"
    })
    assert response.status_code == 401
    assert "Incorrect username or password" in response.json()["detail"]


@pytest.mark.asyncio
async def test_get_me_with_valid_token(setup_test_users):
    """Test getting user info with valid token"""
    db = setup_test_users
    if db is None:
        pytest.skip("Database not available")

        # First login to get token
        login_response = client.post("/auth/login", json={
            "username": "testuser",
            "password": "testpass"
        })
        token = login_response.json()["access_token"]

        # Use token to get user info
        response = client.get("/auth/me", headers={
            "Authorization": f"Bearer {token}"
        })
        assert response.status_code == 200
        data = response.json()
        assert data["username"] == "testuser"
        assert data["role"] == "user"


def test_get_me_with_invalid_token():
    """Test getting user info with invalid token"""
    response = client.get("/auth/me", headers={
        "Authorization": "Bearer invalid_token"
    })
    assert response.status_code == 401


def test_get_me_without_token():
    """Test getting user info without token"""
    response = client.get("/auth/me")
    assert response.status_code == 403  # Forbidden due to missing auth


@pytest.mark.asyncio
async def test_logout(setup_test_users):
    """Test logout endpoint"""
    db = setup_test_users
    if db is None:
        pytest.skip("Database not available")

        # First login to get token
        login_response = client.post("/auth/login", json={
            "username": "testuser",
            "password": "testpass"
        })
        token = login_response.json()["access_token"]

        # Logout
        response = client.post("/auth/logout", headers={
            "Authorization": f"Bearer {token}"
        })
        assert response.status_code == 200
        assert response.json()["message"] == "Logout successful"
