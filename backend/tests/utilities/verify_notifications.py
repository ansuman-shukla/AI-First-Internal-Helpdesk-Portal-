#!/usr/bin/env python3
"""
Comprehensive verification of notification system
"""

import asyncio
import httpx
import json
import time
from motor.motor_asyncio import AsyncIOMotorClient
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

BASE_URL = "http://127.0.0.1:8005"

async def check_database_notifications():
    """Check notifications directly in database"""
    print("🔍 Checking notifications in database...")
    
    mongodb_uri = os.getenv("MONGODB_URI")
    client = AsyncIOMotorClient(mongodb_uri)
    db = client.helpdesk_db
    
    # Count notifications
    notification_count = await db.notifications.count_documents({})
    print(f"📊 Total notifications in database: {notification_count}")
    
    # Get recent notifications
    notifications = await db.notifications.find({}).sort("created_at", -1).limit(10).to_list(length=10)
    
    if notifications:
        print("📋 Recent notifications:")
        for i, notif in enumerate(notifications, 1):
            print(f"  {i}. {notif.get('title', 'N/A')} → User: {notif.get('user_id', 'N/A')} (Read: {notif.get('read', False)})")
            print(f"     Message: {notif.get('message', 'N/A')}")
            print(f"     Type: {notif.get('notification_type', 'N/A')}")
            print(f"     Created: {notif.get('created_at', 'N/A')}")
            print()
    else:
        print("❌ No notifications found in database")
    
    # Check users for context
    users = await db.users.find({}).to_list(length=20)
    print(f"👥 Users in database: {len(users)}")
    
    hr_agents = [u for u in users if u.get('role') == 'hr_agent']
    it_agents = [u for u in users if u.get('role') == 'it_agent']
    admins = [u for u in users if u.get('role') == 'admin']
    regular_users = [u for u in users if u.get('role') == 'user']
    
    print(f"   - HR Agents: {len(hr_agents)}")
    print(f"   - IT Agents: {len(it_agents)}")
    print(f"   - Admins: {len(admins)}")
    print(f"   - Regular Users: {len(regular_users)}")
    
    client.close()
    return notification_count, hr_agents, it_agents, regular_users

async def test_ticket_creation_notification():
    """Test creating a ticket and verify notification creation"""
    print("\n🎫 Testing ticket creation notification...")
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        # Login as a regular user
        print("🔐 Logging in as regular user...")
        login_response = await client.post(
            f"{BASE_URL}/auth/login",
            json={"username": "testuser", "password": "password123"}
        )
        
        if login_response.status_code != 200:
            print(f"❌ Login failed: {login_response.status_code}")
            return False
        
        token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        # Get initial notification count
        initial_count, hr_agents, it_agents, regular_users = await check_database_notifications()
        
        # Create a ticket
        print("📝 Creating a new ticket...")
        ticket_response = await client.post(
            f"{BASE_URL}/tickets/",
            headers=headers,
            json={
                "title": f"Test Notification Ticket {int(time.time())}",
                "description": "This ticket is created to test the notification system",
                "urgency": "medium"
            }
        )
        
        if ticket_response.status_code != 201:
            print(f"❌ Ticket creation failed: {ticket_response.status_code}")
            print(f"Response: {ticket_response.text}")
            return False
        
        ticket_data = ticket_response.json()
        print(f"✅ Ticket created: {ticket_data['ticket_id']}")
        print(f"   Department: {ticket_data.get('department', 'None')}")
        print(f"   Status: {ticket_data.get('status', 'None')}")
        
        # Wait for webhook processing
        print("⏳ Waiting for webhook processing...")
        await asyncio.sleep(3)
        
        # Check notifications again
        final_count, _, _, _ = await check_database_notifications()
        
        new_notifications = final_count - initial_count
        print(f"📈 New notifications created: {new_notifications}")
        
        if new_notifications > 0:
            print("✅ Notification system is working!")
            return True
        else:
            print("❌ No new notifications created")
            return False

async def test_webhook_directly():
    """Test webhook endpoint directly"""
    print("\n🔗 Testing webhook endpoint directly...")
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        # Get initial count
        initial_count, hr_agents, it_agents, regular_users = await check_database_notifications()
        
        # Call webhook directly
        webhook_payload = {
            "ticket_id": f"DIRECT-TEST-{int(time.time())}",
            "user_id": regular_users[0]['_id'] if regular_users else "test_user_id",
            "title": "Direct Webhook Test",
            "description": "Testing webhook directly",
            "urgency": "high",
            "status": "assigned",
            "department": "HR",
            "misuse_flag": False,
            "created_at": "2024-01-01T12:00:00Z"
        }
        
        print(f"📤 Calling webhook with payload: {webhook_payload['ticket_id']}")
        
        webhook_response = await client.post(
            f"{BASE_URL}/internal/webhook/on_ticket_created",
            json=webhook_payload
        )
        
        print(f"📥 Webhook response: {webhook_response.status_code}")
        if webhook_response.status_code == 200:
            print(f"   Response data: {webhook_response.json()}")
        else:
            print(f"   Error: {webhook_response.text}")
        
        # Wait and check notifications
        await asyncio.sleep(2)
        final_count, _, _, _ = await check_database_notifications()
        
        new_notifications = final_count - initial_count
        print(f"📈 New notifications from direct webhook: {new_notifications}")
        
        return new_notifications > 0

async def test_notification_api():
    """Test notification API endpoints"""
    print("\n📡 Testing notification API endpoints...")
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        # Login as HR agent to check their notifications
        print("🔐 Logging in as HR agent...")
        login_response = await client.post(
            f"{BASE_URL}/auth/login",
            json={"username": "hragent", "password": "password123"}
        )
        
        if login_response.status_code != 200:
            print(f"❌ HR agent login failed: {login_response.status_code}")
            return False
        
        token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        # Get notifications via API
        notif_response = await client.get(
            f"{BASE_URL}/notifications",
            headers=headers
        )
        
        if notif_response.status_code == 200:
            notif_data = notif_response.json()
            print(f"📊 HR Agent notifications: {notif_data['total']} total, {notif_data['unread_count']} unread")
            
            if notif_data['notifications']:
                print("📋 Recent notifications for HR agent:")
                for notif in notif_data['notifications'][:3]:
                    print(f"   - {notif['title']}: {notif['message']}")
            
            return True
        else:
            print(f"❌ Failed to get notifications: {notif_response.status_code}")
            return False

async def main():
    """Main verification function"""
    print("🚀 Starting comprehensive notification system verification...")
    print("=" * 60)
    
    try:
        # 1. Check initial database state
        await check_database_notifications()
        
        # 2. Test ticket creation notification
        ticket_test_success = await test_ticket_creation_notification()
        
        # 3. Test webhook directly
        webhook_test_success = await test_webhook_directly()
        
        # 4. Test notification API
        api_test_success = await test_notification_api()
        
        # Summary
        print("\n" + "=" * 60)
        print("📋 VERIFICATION SUMMARY:")
        print(f"   🎫 Ticket Creation Test: {'✅ PASS' if ticket_test_success else '❌ FAIL'}")
        print(f"   🔗 Direct Webhook Test: {'✅ PASS' if webhook_test_success else '❌ FAIL'}")
        print(f"   📡 Notification API Test: {'✅ PASS' if api_test_success else '❌ FAIL'}")
        
        if all([ticket_test_success, webhook_test_success, api_test_success]):
            print("\n🎉 ALL TESTS PASSED! Notification system is fully functional!")
        else:
            print("\n⚠️  Some tests failed. Check the details above.")
        
    except Exception as e:
        print(f"\n❌ Verification failed with error: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
