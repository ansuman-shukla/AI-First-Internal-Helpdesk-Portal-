#!/usr/bin/env python3
"""
Debug script to check ticket ownership and user IDs
"""

import asyncio
import sys
import os
from bson import ObjectId

# Add the backend directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.core.database import connect_to_mongo, close_mongo_connection, get_database


async def debug_tickets():
    """Debug ticket ownership"""
    try:
        # Connect to database
        await connect_to_mongo()
        print("Connected to MongoDB")
        
        db = get_database()
        
        # Get all users
        users_collection = db["users"]
        users = await users_collection.find({}).to_list(length=None)
        
        print("\n=== USERS ===")
        for user in users:
            print(f"User ID: {user['_id']}")
            print(f"Username: {user.get('username', 'N/A')}")
            print(f"Email: {user.get('email', 'N/A')}")
            print(f"Role: {user.get('role', 'N/A')}")
            print(f"Full user data: {user}")
            print("---")
        
        # Get all tickets
        tickets_collection = db["tickets"]
        tickets = await tickets_collection.find({}).to_list(length=None)
        
        print("\n=== TICKETS ===")
        for ticket in tickets:
            print(f"Ticket ID: {ticket['ticket_id']}")
            print(f"MongoDB _id: {ticket['_id']}")
            print(f"Title: {ticket['title']}")
            print(f"User ID: {ticket['user_id']}")
            print(f"Status: {ticket['status']}")
            print(f"Created: {ticket['created_at']}")
            
            # Find the user who owns this ticket
            owner = await users_collection.find_one({"_id": ticket['user_id']})
            if owner:
                print(f"Owner: {owner['username']} ({owner['email']})")
            else:
                print("Owner: NOT FOUND")
            print("---")
        
        print(f"\nTotal Users: {len(users)}")
        print(f"Total Tickets: {len(tickets)}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # Close database connection
        await close_mongo_connection()
        print("Disconnected from MongoDB")


if __name__ == "__main__":
    print("🔍 Debugging tickets and users...")
    asyncio.run(debug_tickets())
