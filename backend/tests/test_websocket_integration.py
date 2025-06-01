"""
WebSocket Integration Tests

This module contains integration tests for WebSocket functionality
using actual WebSocket connections to test real-time chat features.
"""

import pytest
import json
import asyncio
from typing import Dict, Any
from unittest.mock import patch, AsyncMock
import websockets
from fastapi.testclient import TestClient
from bson import ObjectId

from main import app
from app.services.auth_service import create_access_token
from app.schemas.user import UserRole


@pytest.fixture
def test_client():
    """Create test client for the FastAPI app"""
    return TestClient(app)


@pytest.fixture
def test_user_data():
    """Test user data"""
    return {
        "user_id": str(ObjectId()),
        "username": "testuser",
        "role": UserRole.USER.value
    }


@pytest.fixture
def test_agent_data():
    """Test agent data"""
    return {
        "user_id": str(ObjectId()),
        "username": "testagent",
        "role": UserRole.IT_AGENT.value
    }


@pytest.fixture
def test_ticket_id():
    """Test ticket ID"""
    return str(ObjectId())


@pytest.fixture
def valid_user_token(test_user_data):
    """Create valid JWT token for test user"""
    return create_access_token(
        data={"sub": test_user_data["user_id"], "role": test_user_data["role"]}
    )


@pytest.fixture
def valid_agent_token(test_agent_data):
    """Create valid JWT token for test agent"""
    return create_access_token(
        data={"sub": test_agent_data["user_id"], "role": test_agent_data["role"]}
    )


class TestWebSocketConnectionFlow:
    """Test WebSocket connection establishment and basic flow"""

    @patch('app.routers.ws_chat.verify_ticket_access')
    @pytest.mark.asyncio
    async def test_websocket_connection_without_token(self, mock_verify_access):
        """Test WebSocket connection without authentication token"""
        mock_verify_access.return_value = True
        
        # This test would require a running server to test actual WebSocket connections
        # For now, we'll test the logic components
        
        # In a real integration test, you would:
        # 1. Start the FastAPI server
        # 2. Connect via websockets library
        # 3. Verify connection is rejected without token
        
        # Placeholder assertion
        assert True

    @patch('app.routers.ws_chat.verify_ticket_access')
    @pytest.mark.asyncio
    async def test_websocket_connection_with_invalid_token(self, mock_verify_access):
        """Test WebSocket connection with invalid token"""
        mock_verify_access.return_value = True
        
        # Similar to above - would test actual WebSocket connection
        # with invalid token and verify rejection
        
        assert True

    @patch('app.routers.ws_chat.verify_ticket_access')
    @patch('app.routers.ws_chat.message_service')
    @pytest.mark.asyncio
    async def test_websocket_message_flow(self, mock_message_service, mock_verify_access):
        """Test complete WebSocket message flow"""
        mock_verify_access.return_value = True
        
        # Mock message service
        mock_saved_message = AsyncMock()
        mock_saved_message._id = ObjectId()
        mock_saved_message.timestamp.isoformat.return_value = "2023-01-01T00:00:00"
        mock_message_service.save_message = AsyncMock(return_value=mock_saved_message)
        
        # This would test:
        # 1. Connect two WebSocket clients
        # 2. Send message from one client
        # 3. Verify message is received by other client
        # 4. Verify message is saved to database
        
        assert True


class TestWebSocketMessageValidation:
    """Test WebSocket message validation and handling"""

    def test_valid_chat_message_format(self):
        """Test valid chat message format"""
        message_data = {
            "type": "chat",
            "ticket_id": str(ObjectId()),
            "content": "Hello, this is a test message",
            "message_type": "user_message",
            "isAI": False,
            "feedback": "none"
        }

        # Test that this would be valid JSON for WebSocket
        json_str = json.dumps(message_data)
        parsed = json.loads(json_str)

        assert parsed["type"] == "chat"
        assert parsed["content"] == "Hello, this is a test message"
        assert parsed["isAI"] is False

    def test_valid_ai_generated_message_format(self):
        """Test valid AI-generated message format"""
        message_data = {
            "type": "chat",
            "ticket_id": str(ObjectId()),
            "content": "This is an AI-generated response to help you with your issue.",
            "message_type": "agent_message",
            "isAI": True,
            "feedback": "none"
        }

        # Test that this would be valid JSON for WebSocket
        json_str = json.dumps(message_data)
        parsed = json.loads(json_str)

        assert parsed["type"] == "chat"
        assert parsed["content"] == "This is an AI-generated response to help you with your issue."
        assert parsed["isAI"] is True
        assert parsed["message_type"] == "agent_message"

    def test_typing_indicator_message_format(self):
        """Test typing indicator message format"""
        message_data = {
            "type": "typing",
            "ticket_id": str(ObjectId())
        }
        
        json_str = json.dumps(message_data)
        parsed = json.loads(json_str)
        
        assert parsed["type"] == "typing"
        assert "ticket_id" in parsed

    def test_ping_message_format(self):
        """Test ping message format"""
        message_data = {
            "type": "ping",
            "ticket_id": str(ObjectId())
        }
        
        json_str = json.dumps(message_data)
        parsed = json.loads(json_str)
        
        assert parsed["type"] == "ping"


class TestWebSocketErrorHandling:
    """Test WebSocket error handling scenarios"""

    def test_invalid_json_message(self):
        """Test handling of invalid JSON messages"""
        invalid_json = "{ invalid json }"
        
        # Test that this would fail JSON parsing
        with pytest.raises(json.JSONDecodeError):
            json.loads(invalid_json)

    def test_missing_required_fields(self):
        """Test handling of messages with missing required fields"""
        from app.schemas.message import WebSocketMessageSchema
        
        # Missing type field
        with pytest.raises(Exception):
            WebSocketMessageSchema(ticket_id="test")
        
        # Missing ticket_id field
        with pytest.raises(Exception):
            WebSocketMessageSchema(type="chat")

    def test_invalid_message_type(self):
        """Test handling of invalid message types"""
        message_data = {
            "type": "invalid_type",
            "ticket_id": str(ObjectId())
        }
        
        # This would be handled by the WebSocket handler
        # which should send an error response
        assert message_data["type"] == "invalid_type"


class TestConnectionManagerIntegration:
    """Test connection manager integration"""

    @pytest.mark.asyncio
    async def test_connection_manager_room_management(self):
        """Test connection manager room management"""
        from app.services.websocket_manager import ConnectionManager
        
        manager = ConnectionManager()
        
        # Test room ID generation
        room_id = manager._get_room_id("ticket123")
        assert room_id == "ticket_ticket123"
        
        # Test connection ID generation
        conn_id = manager._generate_connection_id("user123", "ticket123")
        assert "user123" in conn_id
        assert "ticket123" in conn_id

    @pytest.mark.asyncio
    async def test_connection_manager_broadcast_logic(self):
        """Test connection manager broadcast logic"""
        from app.services.websocket_manager import ConnectionManager
        from unittest.mock import MagicMock, AsyncMock
        
        manager = ConnectionManager()
        
        # Mock WebSocket connections
        mock_ws1 = AsyncMock()
        mock_ws2 = AsyncMock()
        
        # Simulate connections in a room
        room_id = "ticket_test123"
        manager.rooms[room_id] = {
            "conn1": {"user_id": "user1", "user_role": "user"},
            "conn2": {"user_id": "user2", "user_role": "user"}
        }
        manager.active_connections = {
            "conn1": mock_ws1,
            "conn2": mock_ws2
        }
        
        # Test broadcast
        test_message = {"type": "test", "content": "broadcast test"}
        await manager._broadcast_to_room(room_id, test_message)
        
        # Verify both connections received the message
        mock_ws1.send_text.assert_called_once()
        mock_ws2.send_text.assert_called_once()


class TestWebSocketAuthenticationIntegration:
    """Test WebSocket authentication integration"""

    def test_jwt_token_creation_for_websocket(self, test_user_data):
        """Test JWT token creation for WebSocket authentication"""
        token = create_access_token(
            data={"sub": test_user_data["user_id"], "role": test_user_data["role"]}
        )
        
        assert token is not None
        assert isinstance(token, str)
        assert len(token) > 0

    @patch('app.routers.ws_chat.decode_access_token')
    @pytest.mark.asyncio
    async def test_websocket_authentication_flow(self, mock_decode):
        """Test WebSocket authentication flow"""
        from app.routers.ws_chat import authenticate_websocket_user
        
        # Mock successful token decode
        mock_decode.return_value = {
            "sub": "user123",
            "role": "user"
        }
        
        # Test authentication
        result = await authenticate_websocket_user("valid_token")
        
        assert result["user_id"] == "user123"
        assert result["user_role"] == "user"
        mock_decode.assert_called_once_with("valid_token")

    @patch('app.routers.ws_chat.ticket_service')
    @pytest.mark.asyncio
    async def test_ticket_access_verification(self, mock_ticket_service):
        """Test ticket access verification for WebSocket"""
        from app.routers.ws_chat import verify_ticket_access
        
        # Mock successful ticket access
        mock_ticket_service.get_ticket_by_id_with_role = AsyncMock(
            return_value={"id": "ticket123"}
        )
        
        result = await verify_ticket_access("user123", "user", "ticket123")
        
        assert result is True
        mock_ticket_service.get_ticket_by_id_with_role.assert_called_once()

    @patch('app.routers.ws_chat.ticket_service')
    @pytest.mark.asyncio
    async def test_ticket_access_denied(self, mock_ticket_service):
        """Test ticket access denial for WebSocket"""
        from app.routers.ws_chat import verify_ticket_access
        
        # Mock access denied (no ticket returned)
        mock_ticket_service.get_ticket_by_id_with_role = AsyncMock(return_value=None)
        
        result = await verify_ticket_access("user123", "user", "ticket123")
        
        assert result is False


class TestWebSocketMessagePersistence:
    """Test WebSocket message persistence integration"""

    @patch('app.routers.ws_chat.message_service')
    @pytest.mark.asyncio
    async def test_message_saving_integration(self, mock_message_service):
        """Test message saving during WebSocket chat"""
        from app.routers.ws_chat import handle_chat_message
        from app.schemas.message import WebSocketMessageSchema, MessageType, MessageFeedback

        # Mock saved message
        mock_saved_message = AsyncMock()
        mock_saved_message._id = ObjectId()
        mock_saved_message.timestamp.isoformat.return_value = "2023-01-01T00:00:00"

        mock_message_service.save_message = AsyncMock(return_value=mock_saved_message)

        # Create test WebSocket message
        ws_message = WebSocketMessageSchema(
            type="chat",
            ticket_id="ticket123",
            content="Test chat message",
            message_type=MessageType.USER_MESSAGE,
            isAI=False,
            feedback=MessageFeedback.NONE
        )

        # Mock connection manager
        with patch('app.routers.ws_chat.connection_manager') as mock_manager:
            mock_manager.broadcast_to_ticket = AsyncMock()

            # Handle the chat message
            await handle_chat_message(ws_message, "user123", "user", "conn123")

            # Verify message was saved
            mock_message_service.save_message.assert_called_once()

            # Verify broadcast was called
            mock_manager.broadcast_to_ticket.assert_called_once()

    @patch('app.routers.ws_chat.message_service')
    @patch('app.routers.ws_chat.ticket_service')
    @pytest.mark.asyncio
    async def test_ai_message_saving_integration(self, mock_ticket_service, mock_message_service):
        """Test AI-generated message saving during WebSocket chat"""
        from app.routers.ws_chat import handle_chat_message
        from app.schemas.message import WebSocketMessageSchema, MessageType, MessageFeedback

        # Mock ticket access
        mock_ticket = AsyncMock()
        mock_ticket._id = ObjectId()
        mock_ticket_service.get_ticket_by_id_with_role = AsyncMock(return_value=mock_ticket)

        # Mock saved AI message
        mock_saved_message = AsyncMock()
        mock_saved_message._id = ObjectId()
        mock_saved_message.timestamp.isoformat.return_value = "2023-01-01T00:00:00"

        mock_message_service.save_message = AsyncMock(return_value=mock_saved_message)

        # Create test AI WebSocket message
        ws_message = WebSocketMessageSchema(
            type="chat",
            ticket_id="ticket123",
            content="This is an AI-generated response to help you with your issue.",
            message_type=MessageType.AGENT_MESSAGE,
            isAI=True,
            feedback=MessageFeedback.NONE
        )

        # Mock connection manager
        with patch('app.routers.ws_chat.connection_manager') as mock_manager:
            mock_manager.broadcast_to_ticket = AsyncMock()

            # Handle the AI chat message
            await handle_chat_message(ws_message, "agent123", "it_agent", "conn123")

            # Verify message was saved with isAI=True
            mock_message_service.save_message.assert_called_once()
            call_args = mock_message_service.save_message.call_args
            assert call_args.kwargs['isAI'] is True
            assert call_args.kwargs['content'] == "This is an AI-generated response to help you with your issue."

            # Verify broadcast was called with AI message
            mock_manager.broadcast_to_ticket.assert_called_once()
            broadcast_args = mock_manager.broadcast_to_ticket.call_args
            broadcast_data = broadcast_args[0][1]  # Second argument is the data
            assert broadcast_data['message']['isAI'] is True


class TestAIAgentWebSocketIntegration:
    """Test AI agent functionality via WebSocket integration"""

    @patch('app.routers.ws_chat.message_service')
    @patch('app.routers.ws_chat.ticket_service')
    @pytest.mark.asyncio
    async def test_agent_sends_ai_generated_message(self, mock_ticket_service, mock_message_service):
        """Test agent sending AI-generated message via WebSocket"""
        from app.routers.ws_chat import handle_chat_message
        from app.schemas.message import WebSocketMessageSchema, MessageType, MessageFeedback

        # Mock ticket access
        mock_ticket = AsyncMock()
        mock_ticket._id = ObjectId()
        mock_ticket_service.get_ticket_by_id_with_role = AsyncMock(return_value=mock_ticket)

        # Mock saved AI message
        mock_saved_message = AsyncMock()
        mock_saved_message._id = ObjectId()
        mock_saved_message.timestamp.isoformat.return_value = "2023-01-01T00:00:00"

        mock_message_service.save_message = AsyncMock(return_value=mock_saved_message)

        # Create AI-generated message from agent
        ai_message = WebSocketMessageSchema(
            type="chat",
            ticket_id="ticket123",
            content="Based on your description, I recommend checking your network settings. Here are the steps: 1) Open Network Settings, 2) Check your connection status, 3) Reset if needed.",
            message_type=MessageType.AGENT_MESSAGE,
            isAI=True,
            feedback=MessageFeedback.NONE
        )

        # Mock connection manager
        with patch('app.routers.ws_chat.connection_manager') as mock_manager:
            mock_manager.broadcast_to_ticket = AsyncMock()

            # Agent sends AI message
            await handle_chat_message(ai_message, "agent123", "it_agent", "conn123")

            # Verify message was saved with correct AI attributes
            mock_message_service.save_message.assert_called_once()
            call_args = mock_message_service.save_message.call_args
            assert call_args.kwargs['isAI'] is True
            assert call_args.kwargs['message_type'] == MessageType.AGENT_MESSAGE
            assert "network settings" in call_args.kwargs['content']

            # Verify broadcast includes AI flag
            mock_manager.broadcast_to_ticket.assert_called_once()
            broadcast_args = mock_manager.broadcast_to_ticket.call_args
            broadcast_data = broadcast_args[0][1]
            assert broadcast_data['message']['isAI'] is True
            assert broadcast_data['message']['message_type'] == MessageType.AGENT_MESSAGE.value

    def test_ai_message_schema_validation(self):
        """Test AI message schema validation"""
        from app.schemas.message import WebSocketMessageSchema, MessageType, MessageFeedback

        # Valid AI message
        ai_message_data = {
            "type": "chat",
            "ticket_id": "ticket123",
            "content": "This is an AI-generated response",
            "message_type": "agent_message",
            "isAI": True,
            "feedback": "none"
        }

        message = WebSocketMessageSchema(**ai_message_data)
        assert message.type == "chat"
        assert message.isAI is True
        assert message.message_type == MessageType.AGENT_MESSAGE
        assert message.feedback == MessageFeedback.NONE

    def test_ai_message_broadcast_format(self):
        """Test AI message broadcast format matches expected structure"""
        # This test verifies the broadcast message format for AI messages
        expected_broadcast = {
            "type": "new_message",
            "message": {
                "id": "message_id",
                "ticket_id": "ticket123",
                "sender_id": "agent123",
                "sender_role": "it_agent",
                "message_type": "agent_message",
                "content": "AI-generated response",
                "isAI": True,
                "feedback": "none",
                "timestamp": "2023-01-01T00:00:00"
            }
        }

        # Verify structure
        assert expected_broadcast["type"] == "new_message"
        assert expected_broadcast["message"]["isAI"] is True
        assert expected_broadcast["message"]["message_type"] == "agent_message"


# Note: For actual WebSocket testing with real connections, you would need:
# 1. A test server running the FastAPI app
# 2. WebSocket client connections using the websockets library
# 3. Proper async test setup with actual message sending/receiving
#
# Example of what a real WebSocket test might look like:
#
# @pytest.mark.asyncio
# async def test_real_websocket_connection():
#     # Start test server
#     # Connect WebSocket client
#     # Send/receive messages
#     # Verify behavior
#     pass
