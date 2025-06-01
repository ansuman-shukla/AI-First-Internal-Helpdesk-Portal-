import os
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
from urllib.parse import urlparse

# Load environment variables
load_dotenv()


class Database:
    client: AsyncIOMotorClient = None
    database = None


# Database instance
db = Database()


async def ping_mongodb(uri: str = None, timeout: int = 10) -> dict:
    """
    Ping MongoDB to test connection and return detailed status

    Args:
        uri: MongoDB URI (if None, uses environment variable)
        timeout: Connection timeout in seconds

    Returns:
        dict with connection status and details
    """
    if uri is None:
        uri = os.getenv("MONGODB_URI", "mongodb://localhost:27017/helpdesk_db")

    result = {
        "uri": uri,
        "connected": False,
        "error": None,
        "database_name": None,
        "ping_response": None,
    }

    try:
        # Parse URI to extract database name
        parsed_uri = urlparse(uri)
        if parsed_uri.path and len(parsed_uri.path) > 1:
            result["database_name"] = parsed_uri.path[1:].split("?")[0]
        else:
            result["database_name"] = "helpdesk_db"

        # Create client with timeout
        client = AsyncIOMotorClient(uri, serverSelectionTimeoutMS=timeout * 1000)

        # Test connection with ping
        ping_response = await client.admin.command("ping")
        result["ping_response"] = ping_response
        result["connected"] = ping_response.get("ok") == 1.0

        # Close the test client
        client.close()

    except Exception as e:
        result["error"] = str(e)
        result["connected"] = False

    return result


async def connect_to_mongo():
    """Create database connection"""
    mongodb_uri = os.getenv("MONGODB_URI", "mongodb://localhost:27017/helpdesk_db")

    # First ping to check connection
    ping_result = await ping_mongodb(mongodb_uri)
    if not ping_result["connected"]:
        raise ConnectionError(f"Cannot connect to MongoDB: {ping_result['error']}")

    db.client = AsyncIOMotorClient(mongodb_uri)
    db.database = db.client[ping_result["database_name"]]

    # Final verification
    try:
        await db.client.admin.command("ping")
        print(
            f"Successfully connected to MongoDB database: {ping_result['database_name']}"
        )
    except Exception as e:
        print(f"Failed to connect to MongoDB: {e}")
        raise


async def close_mongo_connection():
    """Close database connection"""
    if db.client:
        db.client.close()
        print("Disconnected from MongoDB")


def get_database():
    """Get database instance"""
    return db.database
