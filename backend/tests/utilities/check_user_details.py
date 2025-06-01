#!/usr/bin/env python3
"""
Check user details in the database
"""

import asyncio
from app.core.database import get_database

async def check_user_details():
    """Check user details in database"""
    
    print("🔍 CHECKING USER DETAILS IN DATABASE")
    print("=" * 50)
    
    try:
        db = get_database()
        if db is None:
            print("❌ Database connection failed!")
            return
        
        # Get all users
        users = await db.users.find({}).to_list(length=100)
        print(f"Found {len(users)} total users:")
        print()
        
        for i, user in enumerate(users, 1):
            print(f"{i}. Username: {user.get('username', 'N/A')}")
            print(f"   Role: {user.get('role', 'N/A')}")
            print(f"   Email: {user.get('email', 'N/A')}")
            print(f"   ID: {user.get('_id', 'N/A')}")
            print(f"   Created: {user.get('created_at', 'N/A')}")
            print()
        
        # Group by role
        print("\n📊 USERS BY ROLE:")
        print("-" * 30)
        
        roles = {}
        for user in users:
            role = user.get('role', 'unknown')
            if role not in roles:
                roles[role] = []
            roles[role].append(user.get('username', 'N/A'))
        
        for role, usernames in roles.items():
            print(f"{role.upper()}: {', '.join(usernames)}")
        
        print("\n💡 SUGGESTED TEST CREDENTIALS:")
        print("-" * 30)
        print("Try these usernames with common passwords:")
        for user in users[:5]:  # Show first 5 users
            username = user.get('username', 'N/A')
            print(f"  Username: {username}")
            print(f"  Try passwords: password123, {username}123, admin123")
            print()
            
    except Exception as e:
        print(f"❌ Error checking users: {str(e)}")

if __name__ == "__main__":
    asyncio.run(check_user_details())
