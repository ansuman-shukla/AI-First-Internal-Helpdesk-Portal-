# WebSocket Real-Time Chat Testing Guide

This guide provides comprehensive instructions for testing the Phase 4 WebSocket real-time chat functionality.

## 🚀 Quick Start

### Prerequisites
- Server running on `http://localhost:8000`
- MongoDB connection established
- Valid user accounts in the system

### 1. Start the Server
```bash
cd backend
uvicorn main:app --reload
```

### 2. Create Test Data

#### Create a User Account
```bash
curl -X POST "http://localhost:8000/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "testuser",
    "password": "testpass123",
    "role": "user"
  }'
```

#### Login and Get JWT Token
```bash
curl -X POST "http://localhost:8000/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "testuser",
    "password": "testpass123"
  }'
```

Save the `access_token` from the response.

#### Create a Test Ticket
```bash
curl -X POST "http://localhost:8000/tickets" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -d '{
    "title": "Test WebSocket Chat",
    "description": "Testing real-time chat functionality",
    "urgency": "medium"
  }'
```

Save the `ticket_id` from the response.

## 🧪 Testing Methods

### Method 1: Using the Test Client Script

1. **Update the test client:**
   ```python
   # In websocket_test_client.py
   TEST_TOKEN = "your_actual_jwt_token_here"
   TEST_TICKET_ID = "your_actual_ticket_id_here"
   ```

2. **Run the test:**
   ```bash
   python websocket_test_client.py
   ```

### Method 2: Using Browser Developer Tools

1. **Open browser and navigate to:** `http://localhost:8000/docs`

2. **Open Developer Console (F12)**

3. **Connect to WebSocket:**
   ```javascript
   const ws = new WebSocket('ws://localhost:8000/ws/chat/YOUR_TICKET_ID?token=YOUR_JWT_TOKEN');
   
   ws.onopen = function(event) {
       console.log('✅ Connected to WebSocket');
   };
   
   ws.onmessage = function(event) {
       console.log('📥 Received:', JSON.parse(event.data));
   };
   
   ws.onclose = function(event) {
       console.log('❌ WebSocket closed:', event.code, event.reason);
   };
   ```

4. **Send test messages:**
   ```javascript
   // Send a chat message
   ws.send(JSON.stringify({
       type: "chat",
       ticket_id: "YOUR_TICKET_ID",
       content: "Hello from browser!",
       message_type: "user_message",
       isAI: false,
       feedback: "none"
   }));
   
   // Send a ping
   ws.send(JSON.stringify({
       type: "ping",
       ticket_id: "YOUR_TICKET_ID"
   }));
   
   // Send typing indicator
   ws.send(JSON.stringify({
       type: "typing",
       ticket_id: "YOUR_TICKET_ID"
   }));
   ```

### Method 3: Using curl for HTTP Endpoints

#### Test Webhook Endpoints
```bash
# Test message sent webhook
curl -X POST "http://localhost:8000/internal/webhook/on_message_sent" \
  -H "Content-Type: application/json" \
  -d '{
    "message_id": "test_message_id",
    "ticket_id": "test_ticket_id",
    "sender_id": "test_user_id",
    "sender_role": "user",
    "message_type": "user_message",
    "content": "Test webhook message",
    "isAI": false,
    "feedback": "none",
    "timestamp": "2023-01-01T00:00:00"
  }'
```

## 🔍 What to Test

### 1. Connection Authentication
- ✅ Connect with valid JWT token
- ❌ Connect without token (should fail with 4001)
- ❌ Connect with invalid token (should fail with 4001)
- ❌ Connect to ticket without access (should fail with 4003)

### 2. Message Types
- ✅ Chat messages with content
- ✅ Typing indicators
- ✅ Ping/pong for connection health
- ❌ Invalid message format (should return error)
- ❌ Missing required fields (should return error)

### 3. Message Broadcasting
- ✅ Messages broadcast to all users in the same ticket room
- ✅ Messages not sent to users in different ticket rooms
- ✅ User join/leave notifications

### 4. Message Persistence
- ✅ Chat messages saved to database
- ✅ Messages retrievable via API
- ✅ Message metadata (timestamp, sender, etc.) correctly stored

### 5. Webhook Integration
- ✅ Message sent webhook fired for each chat message
- ✅ Webhook payload contains correct message data
- ✅ Webhook failures don't break chat functionality

## 📊 Expected Behaviors

### Successful Connection Flow
1. WebSocket connection established
2. User joins ticket room
3. Other users in room receive "user_joined" notification
4. Connection confirmation sent to user

### Chat Message Flow
1. User sends chat message
2. Message validated and saved to database
3. Message broadcast to all users in ticket room
4. Webhook fired with message data
5. All clients receive "new_message" broadcast

### Disconnection Flow
1. User disconnects (gracefully or ungracefully)
2. User removed from room
3. Other users receive "user_left" notification
4. Connection cleaned up

## 🐛 Common Issues and Solutions

### Issue: WebSocket connection fails with 4001
**Solution:** Check JWT token validity and format

### Issue: WebSocket connection fails with 4003
**Solution:** Verify user has access to the ticket

### Issue: Messages not being broadcast
**Solution:** Check that users are in the same ticket room

### Issue: Database connection errors
**Solution:** Ensure MongoDB is running and accessible

### Issue: Webhook failures
**Solution:** Check internal webhook endpoints are accessible

## 📈 Performance Testing

### Load Testing with Multiple Connections
```python
# Use the websocket_test_client.py script
# Modify the test_multiple_clients() function to create more clients
```

### Memory Usage Monitoring
```bash
# Monitor server memory usage during WebSocket connections
ps aux | grep uvicorn
```

## 🔧 Debugging Tips

### Enable Debug Logging
```python
# In main.py or any service file
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Monitor WebSocket Connections
```python
# Check active connections
from app.services.websocket_manager import connection_manager
print(f"Active connections: {connection_manager.get_connection_count()}")
print(f"Active rooms: {connection_manager.get_room_count()}")
```

### Database Query Monitoring
```python
# Check message count for a ticket
from app.services.message_service import message_service
count = await message_service.get_message_count_for_ticket("ticket_id")
print(f"Messages in ticket: {count}")
```

## ✅ Test Checklist

- [ ] WebSocket endpoint accessible at `/ws/chat/{ticket_id}`
- [ ] JWT authentication working for WebSocket connections
- [ ] Ticket access verification working
- [ ] Chat messages being saved to database
- [ ] Messages broadcasting to all room participants
- [ ] Typing indicators working
- [ ] Ping/pong health checks working
- [ ] User join/leave notifications working
- [ ] Webhook firing for message events
- [ ] Error handling for invalid messages
- [ ] Graceful disconnection handling
- [ ] Multiple concurrent connections supported
- [ ] Message persistence across reconnections

## 🎯 Success Criteria

Phase 4 is considered successfully implemented when:

1. **Real-time communication works:** Users can send and receive messages instantly
2. **Authentication is secure:** Only authorized users can access ticket chats
3. **Messages are persistent:** All chat history is saved and retrievable
4. **System is stable:** Handles multiple concurrent connections without issues
5. **Integration works:** Webhooks fire correctly for all message events
6. **Error handling is robust:** System gracefully handles all error scenarios

## 📝 Next Steps

After successful testing of Phase 4:
1. Move to Phase 5: Agent-Side AI Suggestions
2. Consider performance optimizations
3. Add message search functionality
4. Implement file sharing in chat
5. Add emoji and rich text support
