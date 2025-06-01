"""
WebSocket Test Client

This script demonstrates the real-time chat functionality by connecting
to the WebSocket endpoint and sending/receiving messages.

Usage:
    python websocket_test_client.py

Requirements:
    - Server must be running on localhost:8000
    - Valid JWT token (you can get one by logging in via the API)
    - Valid ticket ID that the user has access to
"""

import asyncio
import json
import websockets
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
SERVER_URL = "ws://localhost:8000"
WEBSOCKET_ENDPOINT = "/ws/chat"

# Test data - you'll need to replace these with actual values
TEST_TOKEN = "your_jwt_token_here"  # Get this from /auth/login
TEST_TICKET_ID = "your_ticket_id_here"  # Get this from /tickets


async def websocket_client_demo():
    """
    Demonstrate WebSocket chat functionality
    """
    if TEST_TOKEN == "your_jwt_token_here" or TEST_TICKET_ID == "your_ticket_id_here":
        print("❌ Please update TEST_TOKEN and TEST_TICKET_ID in the script")
        print("   1. Get a JWT token by calling POST /auth/login")
        print("   2. Get a ticket ID by calling GET /tickets")
        return

    # Construct WebSocket URL with authentication
    ws_url = f"{SERVER_URL}{WEBSOCKET_ENDPOINT}/{TEST_TICKET_ID}?token={TEST_TOKEN}"
    
    try:
        print(f"🔗 Connecting to WebSocket: {ws_url}")
        
        async with websockets.connect(ws_url) as websocket:
            print("✅ Connected to WebSocket!")
            
            # Send a ping message
            ping_message = {
                "type": "ping",
                "ticket_id": TEST_TICKET_ID
            }
            
            await websocket.send(json.dumps(ping_message))
            print("📤 Sent ping message")
            
            # Wait for pong response
            response = await websocket.recv()
            pong_data = json.loads(response)
            print(f"📥 Received pong: {pong_data}")
            
            # Send a chat message
            chat_message = {
                "type": "chat",
                "ticket_id": TEST_TICKET_ID,
                "content": f"Hello from WebSocket test client! Time: {datetime.now().isoformat()}",
                "message_type": "user_message",
                "isAI": False,
                "feedback": "none"
            }
            
            await websocket.send(json.dumps(chat_message))
            print("📤 Sent chat message")
            
            # Wait for message confirmation
            response = await websocket.recv()
            message_data = json.loads(response)
            print(f"📥 Received message confirmation: {message_data}")
            
            # Send typing indicator
            typing_message = {
                "type": "typing",
                "ticket_id": TEST_TICKET_ID
            }
            
            await websocket.send(json.dumps(typing_message))
            print("📤 Sent typing indicator")
            
            # Keep connection open for a few seconds to receive any broadcasts
            print("⏳ Waiting for additional messages...")
            try:
                while True:
                    response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                    data = json.loads(response)
                    print(f"📥 Received broadcast: {data}")
            except asyncio.TimeoutError:
                print("⏰ No more messages received")
            
            print("✅ WebSocket test completed successfully!")
            
    except websockets.exceptions.ConnectionClosed as e:
        print(f"❌ WebSocket connection closed: {e}")
    except websockets.exceptions.InvalidStatusCode as e:
        print(f"❌ WebSocket connection failed with status {e.status_code}")
        if e.status_code == 401:
            print("   This usually means the JWT token is invalid or expired")
        elif e.status_code == 403:
            print("   This usually means you don't have access to this ticket")
    except Exception as e:
        print(f"❌ Error: {e}")


async def test_multiple_clients():
    """
    Test multiple WebSocket clients connecting to the same ticket
    """
    if TEST_TOKEN == "your_jwt_token_here" or TEST_TICKET_ID == "your_ticket_id_here":
        print("❌ Please update TEST_TOKEN and TEST_TICKET_ID in the script")
        return

    print("🔗 Testing multiple WebSocket clients...")
    
    ws_url = f"{SERVER_URL}{WEBSOCKET_ENDPOINT}/{TEST_TICKET_ID}?token={TEST_TOKEN}"
    
    async def client_handler(client_id):
        try:
            async with websockets.connect(ws_url) as websocket:
                print(f"✅ Client {client_id} connected")
                
                # Send a message from this client
                message = {
                    "type": "chat",
                    "ticket_id": TEST_TICKET_ID,
                    "content": f"Message from client {client_id}",
                    "message_type": "user_message"
                }
                
                await websocket.send(json.dumps(message))
                print(f"📤 Client {client_id} sent message")
                
                # Listen for messages for a few seconds
                try:
                    while True:
                        response = await asyncio.wait_for(websocket.recv(), timeout=3.0)
                        data = json.loads(response)
                        print(f"📥 Client {client_id} received: {data.get('type', 'unknown')}")
                except asyncio.TimeoutError:
                    pass
                    
                print(f"✅ Client {client_id} finished")
                
        except Exception as e:
            print(f"❌ Client {client_id} error: {e}")
    
    # Run multiple clients concurrently
    await asyncio.gather(
        client_handler(1),
        client_handler(2),
        client_handler(3)
    )
    
    print("✅ Multiple client test completed!")


def print_usage_instructions():
    """Print instructions for using the test client"""
    print("=" * 60)
    print("WebSocket Test Client for AI-First Internal Helpdesk Portal")
    print("=" * 60)
    print()
    print("Before running this test, you need to:")
    print()
    print("1. 🔐 Get a JWT token:")
    print("   POST http://localhost:8000/auth/login")
    print("   Body: {\"username\": \"your_username\", \"password\": \"your_password\"}")
    print()
    print("2. 🎫 Get a ticket ID:")
    print("   GET http://localhost:8000/tickets")
    print("   Header: Authorization: Bearer <your_jwt_token>")
    print()
    print("3. ✏️  Update this script:")
    print("   - Set TEST_TOKEN to your JWT token")
    print("   - Set TEST_TICKET_ID to a valid ticket ID")
    print()
    print("4. 🚀 Run the test:")
    print("   python websocket_test_client.py")
    print()
    print("=" * 60)


async def main():
    """Main function to run WebSocket tests"""
    print_usage_instructions()
    
    print("\n🧪 Running WebSocket Demo...")
    await websocket_client_demo()
    
    print("\n🧪 Running Multiple Clients Test...")
    await test_multiple_clients()


if __name__ == "__main__":
    asyncio.run(main())
