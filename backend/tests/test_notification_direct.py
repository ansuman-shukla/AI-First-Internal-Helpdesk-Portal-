#!/usr/bin/env python3
"""
Direct test of notification service
"""

import requests
import json

# Test the webhook endpoint directly
url = "http://127.0.0.1:8005/internal/webhook/on_ticket_created"

payload = {
    "ticket_id": "TEST-DIRECT-123",
    "user_id": "test_user_id",
    "title": "Direct Test Ticket",
    "description": "Testing webhook directly",
    "urgency": "medium",
    "status": "assigned",
    "department": "HR",
    "misuse_flag": False,
    "created_at": "2024-01-01T12:00:00Z"
}

print("Testing webhook endpoint directly...")
print(f"URL: {url}")
print(f"Payload: {json.dumps(payload, indent=2)}")

try:
    response = requests.post(url, json=payload, timeout=10)
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.text}")
except Exception as e:
    print(f"Error: {str(e)}")
