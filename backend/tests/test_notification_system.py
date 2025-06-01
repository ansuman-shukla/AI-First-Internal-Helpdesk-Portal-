#!/usr/bin/env python3
"""
Test script to verify the notification system is working end-to-end
"""

import asyncio
import httpx
import json
import logging
from datetime import datetime

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BASE_URL = "http://localhost:8000"

async def test_notification_system():
    """Test the complete notification flow"""
    
    print("🔍 TESTING NOTIFICATION SYSTEM")
    print("=" * 50)
    
    async with httpx.AsyncClient() as client:
        
        # Step 1: Login as a user to get authentication token
        print("\n1. 🔐 Testing Authentication...")
        login_data = {
            "username": "testuser",
            "password": "testpass123"
        }
        
        try:
            response = await client.post(f"{BASE_URL}/auth/login", data=login_data)
            if response.status_code == 200:
                auth_data = response.json()
                token = auth_data.get("access_token")
                print(f"✅ Login successful - Token: {token[:20]}...")
                
                headers = {"Authorization": f"Bearer {token}"}
                
                # Step 2: Test notification endpoints
                print("\n2. 📬 Testing Notification Endpoints...")
                
                # Test unread count
                response = await client.get(f"{BASE_URL}/notifications/unread-count", headers=headers)
                print(f"Unread count status: {response.status_code}")
                if response.status_code == 200:
                    count_data = response.json()
                    print(f"✅ Unread notifications: {count_data.get('unread_count', 0)}")
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
                        print(f"  {i}. {notif.get('title', 'N/A')} - {notif.get('type', 'N/A')}")
                else:
                    print(f"❌ Error: {response.text}")
                
            else:
                print(f"❌ Login failed: {response.status_code} - {response.text}")
                
                # Try with a different user
                print("\n🔄 Trying with different credentials...")
                
                # Check if we have any users in the system
                response = await client.get(f"{BASE_URL}/health")
                if response.status_code == 200:
                    print("✅ Server is healthy")
                else:
                    print("❌ Server health check failed")
                    
        except Exception as e:
            print(f"❌ Error during authentication test: {str(e)}")
        
        # Step 3: Test webhook endpoints directly
        print("\n3. 🔗 Testing Webhook Endpoints...")
        
        # Test webhook health
        try:
            response = await client.get(f"{BASE_URL}/internal/webhook/health")
            print(f"Webhook health status: {response.status_code}")
            if response.status_code == 200:
                print("✅ Webhook system is healthy")
            else:
                print(f"❌ Webhook health check failed: {response.text}")
        except Exception as e:
            print(f"❌ Error testing webhook health: {str(e)}")
        
        # Step 4: Test ticket creation webhook
        print("\n4. 🎫 Testing Ticket Creation Webhook...")
        
        webhook_payload = {
            "ticket_id": "TKT-TEST-NOTIFICATION",
            "user_id": "test_user_id",
            "title": "Test Notification Ticket",
            "description": "This is a test ticket to verify notifications",
            "urgency": "medium",
            "status": "assigned",
            "department": "IT",
            "misuse_flag": False,
            "created_at": datetime.utcnow().isoformat()
        }
        
        try:
            response = await client.post(
                f"{BASE_URL}/internal/webhook/on_ticket_created",
                json=webhook_payload
            )
            print(f"Ticket webhook status: {response.status_code}")
            if response.status_code == 200:
                print("✅ Ticket creation webhook successful")
                webhook_response = response.json()
                print(f"Response: {webhook_response.get('message', 'N/A')}")
            else:
                print(f"❌ Ticket webhook failed: {response.text}")
        except Exception as e:
            print(f"❌ Error testing ticket webhook: {str(e)}")
        
        # Step 5: Check database for new notifications
        print("\n5. 🗄️ Checking Database for Notifications...")
        
        # We'll use the simple database check script
        print("Run 'python simple_db_check.py' to see database notifications")
        
    print("\n" + "=" * 50)
    print("🎯 NOTIFICATION SYSTEM TEST COMPLETED!")
    print("\nNext steps:")
    print("1. Check if notifications appear in database after webhook test")
    print("2. Verify frontend is polling notification endpoints")
    print("3. Test real ticket creation flow")


if __name__ == "__main__":
    asyncio.run(test_notification_system())
