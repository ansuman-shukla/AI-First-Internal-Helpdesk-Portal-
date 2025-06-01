#!/usr/bin/env python3
"""
Simple test to check database connection
"""

import asyncio
import os
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

async def test_db_connection():
    """Test database connection"""
    
    print("Testing database connection...")
    
    # Get MongoDB URI from environment
    mongodb_uri = os.getenv("MONGODB_URI")
    if not mongodb_uri:
        print("MONGODB_URI not found in environment variables")
        return
    
    print(f"MongoDB URI: {mongodb_uri[:50]}...")
    
    try:
        # Create client
        client = AsyncIOMotorClient(mongodb_uri)
        
        # Test connection
        await client.admin.command('ping')
        print("Successfully connected to MongoDB!")
        
        # Get database
        db = client.helpdesk_db
        
        # Test collections
        collections = await db.list_collection_names()
        print(f"Available collections: {collections}")
        
        # Test users collection
        users_count = await db.users.count_documents({})
        print(f"Users in database: {users_count}")
        
        # Test tickets collection
        tickets_count = await db.tickets.count_documents({})
        print(f"Tickets in database: {tickets_count}")
        
        # Test notifications collection
        notifications_count = await db.notifications.count_documents({})
        print(f"Notifications in database: {notifications_count}")
        
        # Close connection
        client.close()
        
    except Exception as e:
        print(f"Database connection failed: {str(e)}")

if __name__ == "__main__":
    asyncio.run(test_db_connection())
