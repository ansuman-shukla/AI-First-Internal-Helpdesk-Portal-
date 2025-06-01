#!/usr/bin/env python3
"""
Test notification system via API calls
"""

import asyncio
import httpx
import json

BASE_URL = "http://127.0.0.1:8005"

async def test_api_notifications():
    """Test notifications via API calls"""
    
    print("Testing notification system via API...")
    print("=" * 50)
    
    async with httpx.AsyncClient() as client:
        
        # 1. Login as a user
        print("\n1. Logging in as user...")
        login_response = await client.post(
            f"{BASE_URL}/auth/login",
            json={
                "username": "testuser",
                "password": "password123"
            }
        )
        
        if login_response.status_code != 200:
            print(f"Login failed: {login_response.status_code} - {login_response.text}")
            return
        
        login_data = login_response.json()
        token = login_data["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        print(f"Successfully logged in. Token: {token[:20]}...")
        
        # 2. Check current notifications
        print("\n2. Checking current notifications...")
        notif_response = await client.get(
            f"{BASE_URL}/notifications",
            headers=headers
        )
        
        if notif_response.status_code == 200:
            notif_data = notif_response.json()
            print(f"Current notifications: {notif_data['total']} total, {notif_data['unread_count']} unread")
        else:
            print(f"Failed to get notifications: {notif_response.status_code}")
        
        # 3. Create a new ticket
        print("\n3. Creating a new ticket...")
        ticket_response = await client.post(
            f"{BASE_URL}/tickets/",
            headers=headers,
            json={
                "title": "API Test Ticket for Notifications",
                "description": "This ticket is created via API to test notification system",
                "urgency": "medium"
            }
        )
        
        if ticket_response.status_code == 201:
            ticket_data = ticket_response.json()
            print(f"Successfully created ticket: {ticket_data['ticket_id']}")
            print(f"Ticket department: {ticket_data.get('department', 'None')}")
            print(f"Ticket status: {ticket_data.get('status', 'None')}")
        else:
            print(f"Failed to create ticket: {ticket_response.status_code} - {ticket_response.text}")
            return
        
        # 4. Wait a moment for webhook processing
        print("\n4. Waiting for webhook processing...")
        await asyncio.sleep(3)
        
        # 5. Check notifications again
        print("\n5. Checking notifications after ticket creation...")
        notif_response2 = await client.get(
            f"{BASE_URL}/notifications",
            headers=headers
        )
        
        if notif_response2.status_code == 200:
            notif_data2 = notif_response2.json()
            print(f"Notifications after ticket: {notif_data2['total']} total, {notif_data2['unread_count']} unread")
            
            if notif_data2['notifications']:
                print("Recent notifications:")
                for notif in notif_data2['notifications'][:3]:
                    print(f"  - {notif['title']}: {notif['message']}")
        else:
            print(f"Failed to get notifications: {notif_response2.status_code}")
        
        # 6. Login as an agent to check their notifications
        print("\n6. Checking agent notifications...")
        agent_login_response = await client.post(
            f"{BASE_URL}/auth/login",
            json={
                "username": "hragent",
                "password": "password123"
            }
        )
        
        if agent_login_response.status_code == 200:
            agent_login_data = agent_login_response.json()
            agent_token = agent_login_data["access_token"]
            agent_headers = {"Authorization": f"Bearer {agent_token}"}
            
            print(f"Successfully logged in as agent. Token: {agent_token[:20]}...")
            
            # Check agent notifications
            agent_notif_response = await client.get(
                f"{BASE_URL}/notifications",
                headers=agent_headers
            )
            
            if agent_notif_response.status_code == 200:
                agent_notif_data = agent_notif_response.json()
                print(f"Agent notifications: {agent_notif_data['total']} total, {agent_notif_data['unread_count']} unread")
                
                if agent_notif_data['notifications']:
                    print("Agent notifications:")
                    for notif in agent_notif_data['notifications'][:3]:
                        print(f"  - {notif['title']}: {notif['message']}")
                else:
                    print("No notifications found for agent")
            else:
                print(f"Failed to get agent notifications: {agent_notif_response.status_code}")
        else:
            print(f"Agent login failed: {agent_login_response.status_code}")
        
        # 7. Test webhook endpoint directly
        print("\n7. Testing webhook endpoint directly...")
        webhook_payload = {
            "ticket_id": "TEST-123",
            "user_id": "test_user_id",
            "title": "Direct Webhook Test",
            "description": "Testing webhook directly",
            "urgency": "medium",
            "status": "assigned",
            "department": "HR",
            "misuse_flag": False,
            "created_at": "2024-01-01T12:00:00Z"
        }
        
        webhook_response = await client.post(
            f"{BASE_URL}/internal/webhook/on_ticket_created",
            json=webhook_payload
        )
        
        if webhook_response.status_code == 200:
            print("Webhook endpoint responded successfully")
            webhook_data = webhook_response.json()
            print(f"Webhook response: {webhook_data}")
        else:
            print(f"Webhook endpoint failed: {webhook_response.status_code} - {webhook_response.text}")

if __name__ == "__main__":
    asyncio.run(test_api_notifications())
