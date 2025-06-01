#!/usr/bin/env python3
"""
Simple synchronous database check
"""

import pymongo
import os
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

def check_notifications():
    """Check notifications in database"""
    print("Checking notifications in database...")
    
    # Connect to MongoDB
    client = pymongo.MongoClient(os.getenv("MONGODB_URI"))
    db = client.helpdesk_db
    
    try:
        # Check notifications
        notifications = list(db.notifications.find({}).sort("created_at", -1).limit(10))
        print(f"Total notifications found: {len(notifications)}")
        
        if notifications:
            print("\nRecent notifications:")
            for i, notif in enumerate(notifications, 1):
                print(f"{i}. {notif.get('title', 'N/A')}")
                print(f"   User: {notif.get('user_id', 'N/A')}")
                print(f"   Message: {notif.get('message', 'N/A')}")
                print(f"   Type: {notif.get('notification_type', 'N/A')}")
                print(f"   Read: {notif.get('read', False)}")
                print(f"   Created: {notif.get('created_at', 'N/A')}")
                print()
        else:
            print("No notifications found")
        
        # Check users for context
        users = list(db.users.find({}))
        hr_agents = [u for u in users if u.get('role') == 'hr_agent']
        it_agents = [u for u in users if u.get('role') == 'it_agent']
        admins = [u for u in users if u.get('role') == 'admin']
        regular_users = [u for u in users if u.get('role') == 'user']
        
        print(f"Users in database:")
        print(f"  - HR Agents: {len(hr_agents)}")
        print(f"  - IT Agents: {len(it_agents)}")
        print(f"  - Admins: {len(admins)}")
        print(f"  - Regular Users: {len(regular_users)}")
        
        # Check recent tickets
        tickets = list(db.tickets.find({}).sort("created_at", -1).limit(5))
        print(f"\nRecent tickets: {len(tickets)}")
        for ticket in tickets:
            print(f"  - {ticket.get('ticket_id', 'N/A')}: {ticket.get('title', 'N/A')}")
            print(f"    Department: {ticket.get('department', 'N/A')}, Status: {ticket.get('status', 'N/A')}")
        
    except Exception as e:
        print(f"Error: {str(e)}")
    finally:
        client.close()

if __name__ == "__main__":
    check_notifications()
