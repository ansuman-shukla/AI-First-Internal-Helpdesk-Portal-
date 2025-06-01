#!/usr/bin/env python3
"""
Test notification endpoints directly
"""

import requests
import json

# Test configuration
BASE_URL = "http://127.0.0.1:8000"
TEST_TOKEN = "test-token"  # Using the test token from auth system

def test_notification_endpoints():
    """Test notification endpoints"""
    headers = {
        "Authorization": f"Bearer {TEST_TOKEN}",
        "Content-Type": "application/json"
    }
    
    print("Testing notification endpoints...")
    
    # Test 1: Get unread count
    print("\n1. Testing GET /notifications/unread-count")
    response = requests.get(f"{BASE_URL}/notifications/unread-count", headers=headers)
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"Response: {json.dumps(data, indent=2)}")
    else:
        print(f"Error: {response.text}")
    
    # Test 2: Get notifications
    print("\n2. Testing GET /notifications")
    response = requests.get(f"{BASE_URL}/notifications", headers=headers)
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"Response: {json.dumps(data, indent=2)}")
    else:
        print(f"Error: {response.text}")
    
    # Test 3: Test webhook to create notifications
    print("\n3. Testing webhook to create notifications")
    webhook_payload = {
        "ticket_id": "TKT-TEST-123",
        "title": "Test Notification Ticket",
        "department": "HR",
        "urgency": "medium",
        "status": "open",
        "misuse_flag": False
    }
    
    response = requests.post(
        f"{BASE_URL}/internal/webhook/on_ticket_created",
        json=webhook_payload,
        headers={"Content-Type": "application/json"}
    )
    print(f"Webhook Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"Webhook Response: {json.dumps(data, indent=2)}")
    else:
        print(f"Webhook Error: {response.text}")
    
    # Test 4: Check notifications again after webhook
    print("\n4. Checking notifications after webhook")
    response = requests.get(f"{BASE_URL}/notifications/unread-count", headers=headers)
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"Unread count after webhook: {json.dumps(data, indent=2)}")
    else:
        print(f"Error: {response.text}")

if __name__ == "__main__":
    test_notification_endpoints()
