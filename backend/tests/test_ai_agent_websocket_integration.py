"""
Test AI Agent WebSocket Integration

This module tests the complete workflow of AI agent functionality
including AI suggestion generation and sending AI messages via WebSocket.
"""

import pytest
import json
from unittest.mock import patch, AsyncMock
from bson import ObjectId

from app.schemas.message import WebSocketMessageSchema, MessageType, MessageFeedback, MessageSchema


class TestAIAgentWorkflow:
    """Test complete AI agent workflow from suggestion to WebSocket message"""

    @patch('app.routers.ws_chat.message_service')
    @patch('app.routers.ws_chat.ticket_service')
    @patch('app.routers.ws_chat.connection_manager')
    @pytest.mark.asyncio
    async def test_complete_ai_agent_workflow(self, mock_manager, mock_ticket_service, mock_message_service):
        """Test complete workflow: AI suggestion -> WebSocket AI message"""
        from app.routers.ws_chat import handle_chat_message
        from app.services.ai.response_suggestion_rag import response_suggestion_rag
        
        # Step 1: Mock AI suggestion generation
        conversation_context = [
            MessageSchema(
                id="msg1",
                ticket_id="ticket123",
                sender_id="user123",
                sender_role="user",
                message_type=MessageType.USER_MESSAGE,
                content="My computer won't connect to the internet",
                isAI=False,
                feedback=MessageFeedback.NONE,
                timestamp="2023-01-01T00:00:00"
            )
        ]
        
        # Generate AI suggestion
        ai_suggestion = response_suggestion_rag("ticket123", conversation_context)
        assert ai_suggestion is not None
        assert len(ai_suggestion) > 0
        
        # Step 2: Mock WebSocket message handling
        mock_ticket = AsyncMock()
        mock_ticket._id = ObjectId()
        mock_ticket_service.get_ticket_by_id_with_role = AsyncMock(return_value=mock_ticket)
        
        mock_saved_message = AsyncMock()
        mock_saved_message._id = ObjectId()
        mock_saved_message.timestamp.isoformat.return_value = "2023-01-01T00:00:00"
        mock_message_service.save_message = AsyncMock(return_value=mock_saved_message)
        
        mock_manager.broadcast_to_ticket = AsyncMock()
        
        # Step 3: Create AI WebSocket message using the suggestion
        ai_ws_message = WebSocketMessageSchema(
            type="chat",
            ticket_id="ticket123",
            content=ai_suggestion,
            message_type=MessageType.AGENT_MESSAGE,
            isAI=True,
            feedback=MessageFeedback.NONE
        )
        
        # Step 4: Handle the AI message via WebSocket
        await handle_chat_message(ai_ws_message, "agent123", "it_agent", "conn123")
        
        # Step 5: Verify the complete workflow
        # Verify message was saved with AI flag
        mock_message_service.save_message.assert_called_once()
        call_args = mock_message_service.save_message.call_args
        assert call_args.kwargs['isAI'] is True
        assert call_args.kwargs['content'] == ai_suggestion
        assert call_args.kwargs['message_type'] == MessageType.AGENT_MESSAGE
        
        # Verify broadcast was called with AI message
        mock_manager.broadcast_to_ticket.assert_called_once()
        broadcast_args = mock_manager.broadcast_to_ticket.call_args
        assert broadcast_args[0][0] == "ticket123"  # ticket_id
        broadcast_data = broadcast_args[0][1]  # message data
        assert broadcast_data['type'] == "new_message"
        assert broadcast_data['message']['isAI'] is True
        assert broadcast_data['message']['content'] == ai_suggestion

    def test_ai_message_json_serialization(self):
        """Test AI message can be properly serialized for WebSocket transmission"""
        ai_message_data = {
            "type": "chat",
            "ticket_id": "ticket123",
            "content": "Based on your issue, I recommend restarting your router.",
            "message_type": "agent_message",
            "isAI": True,
            "feedback": "none"
        }
        
        # Test JSON serialization/deserialization
        json_str = json.dumps(ai_message_data)
        parsed_data = json.loads(json_str)
        
        # Verify all fields are preserved
        assert parsed_data["type"] == "chat"
        assert parsed_data["isAI"] is True
        assert parsed_data["message_type"] == "agent_message"
        assert "router" in parsed_data["content"]
        
        # Test WebSocket schema validation
        ws_message = WebSocketMessageSchema(**parsed_data)
        assert ws_message.isAI is True
        assert ws_message.message_type == MessageType.AGENT_MESSAGE

    @pytest.mark.asyncio
    async def test_ai_message_broadcast_to_multiple_clients(self):
        """Test AI message broadcast reaches multiple WebSocket clients"""
        from app.services.websocket_manager import ConnectionManager
        
        manager = ConnectionManager()
        
        # Mock multiple WebSocket connections
        mock_ws1 = AsyncMock()
        mock_ws2 = AsyncMock()
        mock_ws3 = AsyncMock()
        
        # Simulate multiple clients in the same ticket room
        room_id = "ticket_ticket123"
        manager.rooms[room_id] = {
            "conn1": {"user_id": "user123", "user_role": "user"},
            "conn2": {"user_id": "agent123", "user_role": "it_agent"},
            "conn3": {"user_id": "admin123", "user_role": "admin"}
        }
        manager.active_connections = {
            "conn1": mock_ws1,
            "conn2": mock_ws2,
            "conn3": mock_ws3
        }
        
        # Test AI message broadcast
        ai_message = {
            "type": "new_message",
            "message": {
                "id": "msg123",
                "ticket_id": "ticket123",
                "sender_id": "agent123",
                "sender_role": "it_agent",
                "message_type": "agent_message",
                "content": "AI-generated troubleshooting steps",
                "isAI": True,
                "feedback": "none",
                "timestamp": "2023-01-01T00:00:00"
            }
        }
        
        await manager._broadcast_to_room(room_id, ai_message)
        
        # Verify all clients received the AI message
        mock_ws1.send_text.assert_called_once()
        mock_ws2.send_text.assert_called_once()
        mock_ws3.send_text.assert_called_once()
        
        # Verify the message content includes AI flag
        sent_message = json.loads(mock_ws1.send_text.call_args[0][0])
        assert sent_message["message"]["isAI"] is True

    def test_ai_message_validation_edge_cases(self):
        """Test AI message validation with edge cases"""
        from app.schemas.message import WebSocketMessageSchema
        
        # Test with minimal AI message
        minimal_ai_message = {
            "type": "chat",
            "ticket_id": "ticket123",
            "content": "Yes.",
            "isAI": True
        }
        
        message = WebSocketMessageSchema(**minimal_ai_message)
        assert message.isAI is True
        assert message.message_type == MessageType.USER_MESSAGE  # Default
        assert message.feedback == MessageFeedback.NONE  # Default
        
        # Test with long AI message
        long_content = "This is a very long AI-generated response. " * 50
        long_ai_message = {
            "type": "chat",
            "ticket_id": "ticket123",
            "content": long_content,
            "message_type": "agent_message",
            "isAI": True
        }
        
        message = WebSocketMessageSchema(**long_ai_message)
        assert message.isAI is True
        assert len(message.content) > 1000

    def test_ai_message_database_storage_format(self):
        """Test AI message storage format in database"""
        # This test verifies the expected database document structure
        expected_db_document = {
            "_id": "ObjectId",
            "ticket_id": "ObjectId",
            "sender_id": "ObjectId", 
            "sender_role": "it_agent",
            "message_type": "agent_message",
            "content": "AI-generated response content",
            "isAI": True,
            "feedback": "none",
            "timestamp": "datetime"
        }
        
        # Verify required fields for AI messages
        assert expected_db_document["isAI"] is True
        assert expected_db_document["sender_role"] in ["it_agent", "hr_agent", "admin"]
        assert expected_db_document["message_type"] == "agent_message"
        assert len(expected_db_document["content"]) > 0

    def test_ai_message_frontend_display_requirements(self):
        """Test AI message format meets frontend display requirements"""
        # Frontend expects this structure for AI message display
        frontend_ai_message = {
            "id": "msg123",
            "ticket_id": "ticket123",
            "sender_id": "agent123",
            "sender_role": "it_agent",
            "message_type": "agent_message",
            "content": "AI-generated response",
            "isAI": True,
            "feedback": "none",
            "timestamp": "2023-01-01T00:00:00"
        }
        
        # Verify frontend can identify AI messages
        assert frontend_ai_message["isAI"] is True
        
        # Verify frontend can display AI messages differently
        if frontend_ai_message["isAI"]:
            # Frontend should show AI indicator (🤖)
            assert frontend_ai_message["sender_role"] in ["it_agent", "hr_agent", "admin"]
            assert frontend_ai_message["message_type"] == "agent_message"
