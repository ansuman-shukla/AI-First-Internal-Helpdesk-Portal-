#!/usr/bin/env python3
"""
Simple test to check notifications in database
"""

import asyncio
import os
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

async def check_notifications():
    """Check notifications in database"""
    
    print("Checking notifications in database...")
    
    # Get MongoDB URI from environment
    mongodb_uri = os.getenv("MONGODB_URI")
    if not mongodb_uri:
        print("MONGODB_URI not found in environment variables")
        return
    
    try:
        # Create client
        client = AsyncIOMotorClient(mongodb_uri)
        
        # Get database
        db = client.helpdesk_db
        
        # Check notifications
        notifications = await db.notifications.find({}).to_list(length=100)
        print(f"Total notifications in database: {len(notifications)}")
        
        if notifications:
            print("Recent notifications:")
            for notif in notifications[-5:]:  # Show last 5
                print(f"  - {notif.get('title', 'N/A')} for user {notif.get('user_id', 'N/A')} (read: {notif.get('read', False)})")
        else:
            print("No notifications found in database")
        
        # Check tickets
        tickets = await db.tickets.find({}).to_list(length=10)
        print(f"\nTotal tickets in database: {len(tickets)}")
        
        if tickets:
            print("Recent tickets:")
            for ticket in tickets[-3:]:  # Show last 3
                print(f"  - {ticket.get('ticket_id', 'N/A')}: {ticket.get('title', 'N/A')} (status: {ticket.get('status', 'N/A')})")
        
        # Close connection
        client.close()
        
    except Exception as e:
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    asyncio.run(check_notifications())
