#!/usr/bin/env python3
"""
Test script to verify frontend authentication and notification access
"""

import asyncio
import httpx
import json
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BASE_URL = "http://localhost:8000"

async def test_frontend_auth_flow():
    """Test the authentication flow that frontend would use"""
    
    print("🔍 TESTING FRONTEND AUTHENTICATION FLOW")
    print("=" * 50)
    
    async with httpx.AsyncClient() as client:
        
        # Step 1: Try to login with a real user
        print("\n1. 🔐 Testing Login with Real Users...")
        
        # First, let's see what users exist
        try:
            # Try to get users from database (we'll need to check the database)
            print("Checking available users in database...")
            
            # Let's try some common test credentials
            test_credentials = [
                {"username": "admin", "password": "admin123"},
                {"username": "testuser", "password": "testpass123"},
                {"username": "itagent", "password": "password123"},
                {"username": "hragent", "password": "password123"},
                {"username": "user1", "password": "password123"},
            ]
            
            successful_login = None
            
            for creds in test_credentials:
                try:
                    # Use form data for login (not JSON)
                    response = await client.post(
                        f"{BASE_URL}/auth/login", 
                        data=creds,  # Use data instead of json
                        headers={"Content-Type": "application/x-www-form-urlencoded"}
                    )
                    
                    if response.status_code == 200:
                        auth_data = response.json()
                        token = auth_data.get("access_token")
                        print(f"✅ Login successful with {creds['username']} - Token: {token[:20]}...")
                        successful_login = {"token": token, "username": creds['username']}
                        break
                    else:
                        print(f"❌ Login failed for {creds['username']}: {response.status_code}")
                        
                except Exception as e:
                    print(f"❌ Error testing {creds['username']}: {str(e)}")
            
            if successful_login:
                token = successful_login["token"]
                username = successful_login["username"]
                headers = {"Authorization": f"Bearer {token}"}
                
                # Step 2: Test notification endpoints with valid auth
                print(f"\n2. 📬 Testing Notification Endpoints with {username}...")
                
                # Test unread count
                response = await client.get(f"{BASE_URL}/notifications/unread-count", headers=headers)
                print(f"Unread count status: {response.status_code}")
                if response.status_code == 200:
                    count_data = response.json()
                    print(f"✅ Unread notifications: {count_data.get('unread_count', 0)}")
                    print(f"✅ Total notifications: {count_data.get('total_count', 0)}")
                else:
                    print(f"❌ Error: {response.text}")
                
                # Test get notifications
                response = await client.get(f"{BASE_URL}/notifications", headers=headers)
                print(f"Get notifications status: {response.status_code}")
                if response.status_code == 200:
                    notifications_data = response.json()
                    notifications = notifications_data.get('notifications', [])
                    print(f"✅ Found {len(notifications)} notifications")
                    
                    # Show recent notifications
                    for i, notif in enumerate(notifications[:3], 1):
                        print(f"  {i}. {notif.get('title', 'N/A')} - {notif.get('type', 'N/A')} - Read: {notif.get('read', False)}")
                else:
                    print(f"❌ Error: {response.text}")
                
                # Step 3: Test current user endpoint
                print(f"\n3. 👤 Testing Current User Endpoint...")
                response = await client.get(f"{BASE_URL}/auth/me", headers=headers)
                print(f"Current user status: {response.status_code}")
                if response.status_code == 200:
                    user_data = response.json()
                    print(f"✅ Current user: {user_data.get('username')} ({user_data.get('role')})")
                else:
                    print(f"❌ Error: {response.text}")
                    
            else:
                print("❌ No successful login found. Need to check user credentials.")
                print("\nTry running this to see users in database:")
                print("python simple_db_check.py")
                
        except Exception as e:
            print(f"❌ Error during authentication test: {str(e)}")
    
    print("\n" + "=" * 50)
    print("🎯 FRONTEND AUTHENTICATION TEST COMPLETED!")


if __name__ == "__main__":
    asyncio.run(test_frontend_auth_flow())
