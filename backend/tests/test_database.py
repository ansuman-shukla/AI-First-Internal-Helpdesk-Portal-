import pytest
from app.core.database import connect_to_mongo, close_mongo_connection, get_database, db, ping_mongodb
from dotenv import load_dotenv

load_dotenv()


@pytest.mark.asyncio
async def test_mongodb_ping():
    """Test MongoDB ping function with detailed diagnostics"""
    result = await ping_mongodb()

    print(f"\n--- MongoDB Ping Test Results ---")
    print(f"URI: {result['uri']}")
    print(f"Database Name: {result['database_name']}")
    print(f"Connected: {result['connected']}")
    print(f"Error: {result['error']}")
    print(f"Ping Response: {result['ping_response']}")

    if not result['connected']:
        pytest.skip(f"MongoDB not available: {result['error']}")

    assert result['connected'] is True
    assert result['ping_response']['ok'] == 1.0


@pytest.mark.asyncio
async def test_database_connection():
    """Test that we can successfully connect to MongoDB"""
    # First check if MongoDB is available using ping
    ping_result = await ping_mongodb()
    if not ping_result['connected']:
        pytest.skip(f"MongoDB not available: {ping_result['error']}")

    try:
        # Test connection
        await connect_to_mongo()

        # Verify we have a database instance
        database = get_database()
        assert database is not None

        # Test that we can perform a basic operation
        # Try to ping the database
        result = await db.client.admin.command('ping')
        assert result['ok'] == 1.0

    except Exception as e:
        pytest.fail(f"Database connection failed: {e}")

    finally:
        # Clean up
        await close_mongo_connection()


@pytest.mark.asyncio
async def test_get_database_before_connection():
    """Test that get_database returns None before connection is established"""
    # Reset database instance
    db.database = None
    database = get_database()
    assert database is None
