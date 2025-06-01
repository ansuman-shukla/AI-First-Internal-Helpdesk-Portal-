#!/usr/bin/env python3
"""
Script to seed the database with an admin user for testing purposes.
Run this script to create an admin user with credentials: admin/admin123
"""

import asyncio
import sys
import os
from datetime import datetime, timezone

# Add the backend directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.core.database import connect_to_mongo, close_mongo_connection, get_database
from app.schemas.user import UserCreateSchema, UserRole
from app.services.user_service import user_service


async def seed_admin_user():
    """Create an admin user for testing"""
    try:
        # Connect to database
        await connect_to_mongo()
        print("Connected to MongoDB")
        
        # Check if admin user already exists
        existing_admin = await user_service.get_user_by_username("admin")
        if existing_admin:
            print("Admin user already exists!")
            return
        
        # Create admin user
        admin_data = UserCreateSchema(
            username="admin",
            email="admin@helpdesk.com",
            password="admin123",
            role=UserRole.ADMIN
        )
        
        admin_user = await user_service.create_user(admin_data)
        print(f"✅ Admin user created successfully!")
        print(f"   Username: admin")
        print(f"   Email: admin@helpdesk.com")
        print(f"   Password: admin123")
        print(f"   Role: {admin_user.role.value}")
        print(f"   Created at: {admin_user.created_at}")
        
        # Create a test regular user
        user_data = UserCreateSchema(
            username="testuser",
            email="user@helpdesk.com",
            password="password123",
            role=UserRole.USER
        )
        
        test_user = await user_service.create_user(user_data)
        print(f"✅ Test user created successfully!")
        print(f"   Username: testuser")
        print(f"   Email: user@helpdesk.com")
        print(f"   Password: password123")
        print(f"   Role: {test_user.role.value}")
        
        # Create test IT agent
        it_agent_data = UserCreateSchema(
            username="itagent",
            email="it@helpdesk.com",
            password="password123",
            role=UserRole.IT_AGENT
        )
        
        it_agent = await user_service.create_user(it_agent_data)
        print(f"✅ IT Agent created successfully!")
        print(f"   Username: itagent")
        print(f"   Email: it@helpdesk.com")
        print(f"   Password: password123")
        print(f"   Role: {it_agent.role.value}")
        
        # Create test HR agent
        hr_agent_data = UserCreateSchema(
            username="hragent",
            email="hr@helpdesk.com",
            password="password123",
            role=UserRole.HR_AGENT
        )
        
        hr_agent = await user_service.create_user(hr_agent_data)
        print(f"✅ HR Agent created successfully!")
        print(f"   Username: hragent")
        print(f"   Email: hr@helpdesk.com")
        print(f"   Password: password123")
        print(f"   Role: {hr_agent.role.value}")
        
        print("\n🎉 Database seeded successfully!")
        print("\nYou can now login with any of these accounts:")
        print("- Admin: admin / admin123")
        print("- User: testuser / password123")
        print("- IT Agent: itagent / password123")
        print("- HR Agent: hragent / password123")
        
    except Exception as e:
        print(f"❌ Error seeding database: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # Close database connection
        await close_mongo_connection()
        print("Disconnected from MongoDB")


if __name__ == "__main__":
    print("🌱 Seeding database with test users...")
    asyncio.run(seed_admin_user())
