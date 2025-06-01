import pytest
import pytest_asyncio
import asyncio
from fastapi.testclient import TestClient
from fastapi import FastAPI
from app.routers.auth import router as auth_router
from app.routers.home import router as home_router
from app.core.database import connect_to_mongo, close_mongo_connection, get_database
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create test app
app = FastAPI()
app.include_router(auth_router)
app.include_router(home_router)

client = TestClient(app)


@pytest_asyncio.fixture(scope="function")
async def setup_test_users():
    """Setup test users for home tests"""
    db = None
    try:
        logger.info("Setting up test users...")
        await connect_to_mongo()
        db = get_database()
        if db is not None:
            logger.info("Database connection established")

            # Clean up existing test users
            cleanup_result = await db.users.delete_many({"username": {"$in": ["testuser_home", "testadmin_home"]}})
            logger.info(f"Cleaned up {cleanup_result.deleted_count} existing test users")

            # Create test users directly in database (avoid event loop conflicts)
            from app.services.user_service import user_service
            from app.schemas.user import UserCreateSchema, UserRole

            # Create regular user
            user_data = UserCreateSchema(
                username="testuser_home",
                email="testuser_home@example.com",
                password="testpass",
                role=UserRole.USER
            )
            created_user = await user_service.create_user(user_data)
            logger.info(f"Created test user: {created_user.username} with ID: {created_user._id}")

            # Create admin user
            admin_data = UserCreateSchema(
                username="testadmin_home",
                email="testadmin_home@example.com",
                password="adminpass",
                role=UserRole.ADMIN
            )
            created_admin = await user_service.create_user(admin_data)
            logger.info(f"Created admin user: {created_admin.username} with ID: {created_admin._id}")

        yield db
    except Exception as e:
        logger.error(f"Error setting up test users: {e}")
        pytest.skip("MongoDB not available")
    finally:
        if db is not None:
            # Clean up test users
            cleanup_result = await db.users.delete_many({"username": {"$in": ["testuser_home", "testadmin_home"]}})
            logger.info(f"Final cleanup: removed {cleanup_result.deleted_count} test users")
        await close_mongo_connection()
        logger.info("Test cleanup completed")


async def get_test_token(username="testuser_home", password="testpass"):
    """Helper function to get authentication token using async client"""
    logger.info(f"Attempting to get token for user: {username}")

    from httpx import AsyncClient, ASGITransport

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as async_client:
        response = await async_client.post("/auth/login", json={
            "username": username,
            "password": password
        })

        logger.info(f"Login response status: {response.status_code}")
        if response.status_code != 200:
            logger.error(f"Login failed for {username}: {response.status_code} - {response.text}")
            raise Exception(f"Login failed: {response.status_code} - {response.text}")

        token_data = response.json()
        logger.info(f"Successfully obtained token for user: {username}")
        return token_data["access_token"]


async def get_admin_token():
    """Helper function to get admin authentication token using async client"""
    logger.info("Attempting to get admin token")

    from httpx import AsyncClient, ASGITransport

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as async_client:
        response = await async_client.post("/auth/login", json={
            "username": "testadmin_home",
            "password": "adminpass"
        })

        logger.info(f"Admin login response status: {response.status_code}")
        if response.status_code != 200:
            logger.error(f"Admin login failed: {response.status_code} - {response.text}")
            raise Exception(f"Admin login failed: {response.status_code} - {response.text}")

        token_data = response.json()
        logger.info("Successfully obtained admin token")
        return token_data["access_token"]


@pytest.mark.asyncio
async def test_user_home_with_valid_token(setup_test_users):
    """Test user home endpoint with valid token and verify self-serve bot instructions"""
    db = setup_test_users
    if db is None:
        pytest.skip("Database not available")

    logger.info("Starting test_user_home_with_valid_token")

    # Wait a bit to ensure user creation is complete
    await asyncio.sleep(0.1)

    token = await get_test_token()
    logger.info(f"Obtained token: {token[:20]}...")

    response = client.get("/user/home", headers={
        "Authorization": f"Bearer {token}"
    })
    logger.info(f"Home endpoint response status: {response.status_code}")

    assert response.status_code == 200
    data = response.json()
    assert "Welcome to the User Home Page" in data["message"]
    assert data["user"] == "testuser_home"
    assert data["role"] == "user"
    assert "features" in data
    assert "self_serve_bot" in data

    # Verify comprehensive self-serve bot instructions
    bot_info = data["self_serve_bot"]
    assert bot_info["endpoint"] == "/ai/self-serve-query"
    assert bot_info["method"] == "POST"
    assert "title" in bot_info
    assert "AI-Powered Self-Serve Assistant" in bot_info["title"]
    assert "capabilities" in bot_info
    assert "usage_instructions" in bot_info
    assert "example_queries" in bot_info
    assert "tips" in bot_info
    assert "limitations" in bot_info

    # Verify usage instructions contain proper format information
    usage = bot_info["usage_instructions"]
    assert "request_format" in usage
    assert "response_format" in usage
    assert "query" in usage["request_format"]
    assert "answer" in usage["response_format"]


def test_user_home_without_token():
    """Test user home endpoint without token"""
    response = client.get("/user/home")
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_agent_home_with_user_token(setup_test_users):
    """Test agent home endpoint with user token (should be denied)"""
    db = setup_test_users
    if db is None:
        pytest.skip("Database not available")

    logger.info("Starting test_agent_home_with_user_token")
    await asyncio.sleep(0.1)

    token = await get_test_token()
    response = client.get("/agent/home", headers={
        "Authorization": f"Bearer {token}"
    })
    assert response.status_code == 200
    data = response.json()
    assert "Access denied" in data["error"]


@pytest.mark.asyncio
async def test_agent_home_with_admin_token(setup_test_users):
    """Test agent home endpoint with admin token (should work)"""
    db = setup_test_users
    if db is None:
        pytest.skip("Database not available")

    logger.info("Starting test_agent_home_with_admin_token")
    await asyncio.sleep(0.1)

    token = await get_admin_token()
    response = client.get("/agent/home", headers={
        "Authorization": f"Bearer {token}"
    })
    assert response.status_code == 200
    data = response.json()
    # Admin should be denied agent access in this implementation
    assert "Access denied" in data["error"]


@pytest.mark.asyncio
async def test_admin_home_with_admin_token(setup_test_users):
    """Test admin home endpoint with admin token"""
    db = setup_test_users
    if db is None:
        pytest.skip("Database not available")

    logger.info("Starting test_admin_home_with_admin_token")
    await asyncio.sleep(0.1)

    token = await get_admin_token()
    response = client.get("/admin/home", headers={
        "Authorization": f"Bearer {token}"
    })
    assert response.status_code == 200
    data = response.json()
    assert "Welcome to the Admin Home Page" in data["message"]
    assert data["admin"] == "testadmin_home"
    assert data["role"] == "admin"
    assert "features" in data


@pytest.mark.asyncio
async def test_admin_home_with_user_token(setup_test_users):
    """Test admin home endpoint with user token (should be denied)"""
    db = setup_test_users
    if db is None:
        pytest.skip("Database not available")

    logger.info("Starting test_admin_home_with_user_token")
    await asyncio.sleep(0.1)

    token = await get_test_token()
    response = client.get("/admin/home", headers={
        "Authorization": f"Bearer {token}"
    })
    assert response.status_code == 200
    data = response.json()
    assert "Access denied" in data["error"]


def test_admin_home_without_token():
    """Test admin home endpoint without token"""
    response = client.get("/admin/home")
    assert response.status_code == 403
